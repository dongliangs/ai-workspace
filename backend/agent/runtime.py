# agent/runtime.py
"""
ReAct Runtime —— Agent 循环（Thought → Action → Observation）。
===========================================================================
ReAct (Reason + Act) 模式：

    Loop:
      1. THOUGHT     调用 LLM，带上 context + tools
                     LLM 推理：该不该用工具？用哪个？传什么参数？
                     → 返回文本（推理/最终回答）或 tool_calls（行动）

      2. FINAL?      如果 LLM 没有返回 tool_calls → 最终回答，结束

      3. ACTION      执行 LLM 选择的工具
                     → 通过 Executor 调用 handler，得到 ToolResult

      4. OBSERVATION 把工具结果追加到 context
                     → LLM 下一轮能看到工具执行了什么、返回了什么

      5. 回到步骤 1

事件流（SSE）：
    agent_start → text → tool_start → tool_result → text → ... → (done)

无工具时退化为普通对话：LLM 直接返回文本，不产生 tool 事件。
===========================================================================
"""
import json
import logging
from typing import Any, AsyncGenerator

from agent.executor import execute_tool
from agent.prompts import SYSTEM_PROMPT
from agent.registry import ToolRegistry, registry
from agent.schema import ToolResult
from services.llm_service import chat_with_tools

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


class AgentContext:
    """
    Agent 运行上下文 —— 维护发送给 LLM 的完整消息列表。

    消息类型：
    - system:    Agent 角色与规则（SYSTEM_PROMPT）
    - user:      用户输入
    - assistant: LLM 回复（可能含 tool_calls）
    - tool:      工具执行结果（Observation）
    """

    def __init__(
        self,
        system_prompt: str = "",
        user_id: int = 0,
        kb_id: int = 0,
    ) -> None:
        self.messages: list[dict[str, Any]] = []
        # 会话身份上下文：由 API 层注入，供 Executor 下发给需要的工具
        # （如 knowledge_search），LLM 无法感知和伪造
        self.user_id = user_id
        self.kb_id = kb_id
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_history(self, history: list[dict[str, Any]]) -> None:
        """添加对话历史消息。"""
        self.messages.extend(history)

    def add_user_message(self, content: str) -> None:
        """添加当前用户消息。"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, message: dict[str, Any]) -> None:
        """
        添加 assistant 消息（含 tool_calls）到上下文。

        当 LLM 决定调用工具（Action），必须把这条 assistant 消息
        加入上下文，然后追加工具结果（Observation），LLM 才能关联。
        """
        self.messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """添加工具执行结果（Observation）到上下文。"""
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        )


class AgentRuntime:
    """
    ReAct Runtime：执行 Thought → Action → Observation 循环。

    通过 run() 异步生成器 yield SSE 事件 dict，
    调用方（agent_service）负责序列化为 SSE 帧并持久化最终消息。
    """

    def __init__(self, tool_registry: ToolRegistry = registry) -> None:
        self.registry = tool_registry

    async def run(
        self,
        context: AgentContext,
        tool_names: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        运行 ReAct 循环。

        Args:
            context:    Agent 上下文（已含 system prompt、历史、用户消息）
            tool_names: 可选，限制本次可用工具子集；None=全部已注册工具

        Yields:
            SSE 事件 dict:
            - {"type": "agent_start"}
            - {"type": "text", "content": "..."}
            - {"type": "tool_start", "tool": "...", "arguments": {...}}
            - {"type": "tool_result", "tool": "...", "status": "...", "result": {...}}
            # done 事件由 agent_service 发送
        """
        yield {"type": "agent_start"}

        # 获取传给 LLM 的工具 Schema
        tool_defs = self.registry.get_definitions(tool_names)
        has_tools = len(tool_defs) > 0

        for iteration in range(MAX_ITERATIONS):
            logger.info("ReAct 第 %d 轮 (Thought)", iteration + 1)

            # ---- 1. THOUGHT: 调用 LLM ----
            try:
                response = await chat_with_tools(context.messages, tool_defs)
            except Exception as e:
                logger.exception("LLM 调用失败")
                yield {"type": "text", "content": f"Agent 调用 AI 服务时出错: {e}"}
                return

            message = response.choices[0].message

            # 推理文本 → 推送给前端
            if message.content:
                yield {"type": "text", "content": message.content}

            # ---- 2. FINAL: 无 tool_calls → 最终回答 ----
            if not message.tool_calls:
                logger.info("Agent 完成，共 %d 轮", iteration + 1)
                return

            # ---- 3. ACTION: 构造 assistant 消息加入上下文 ----
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            context.add_assistant_message(assistant_msg)

            # ---- 4. ACTION + OBSERVATION: 执行每个工具 ----
            for tc in message.tool_calls:
                tool_name = tc.function.name

                # 解析 LLM 生成的参数
                try:
                    arguments = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                # Action: 通知前端工具开始执行
                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "arguments": arguments,
                }

                # Action: 执行工具（executor 返回 ToolResult，不抛异常）
                # 会话上下文（user_id/kb_id）由服务端注入，LLM 参数不可覆盖
                result: ToolResult = await execute_tool(
                    tool_name,
                    arguments,
                    context={
                        "user_id": context.user_id,
                        "kb_id": context.kb_id,
                    },
                )

                # Observation: 通知前端工具执行结果
                yield {
                    "type": "tool_result",
                    "tool": result.tool,
                    "status": result.status,
                    "result": result.data if result.status == "success" else result.error,
                }

                # Observation: 工具结果加入上下文，供下一轮 LLM 使用
                context.add_tool_result(tc.id, result.to_content())

        # 超过最大迭代次数
        logger.warning("Agent 达到最大循环次数 %d", MAX_ITERATIONS)
        yield {
            "type": "text",
            "content": "Agent 已达到最大执行轮次限制，请尝试简化任务。",
        }
