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
import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from agent.executor import execute_tool
from agent.prompts import SYSTEM_PROMPT
from agent.registry import ToolRegistry, registry
from agent.schema import ToolResult
from services.llm_service import chat_with_tools_stream

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
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        运行 ReAct 循环。

        Args:
            context:    Agent 上下文（已含 system prompt、历史、用户消息）
            tool_names: 可选，限制本次可用工具子集；None=全部已注册工具
            cancel_event: 用户停止生成信号，在一个事件边界检查

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

            if cancel_event is not None and cancel_event.is_set():
                yield {"type": "generation_cancelled"}
                return

            # ---- 1. THOUGHT: 流式调用 LLM ----
            # 文本增量边生成边推送；tool_calls 以增量碎片形式返回，按 index 拼装
            text_parts: list[str] = []
            pending_calls: dict[int, dict[str, str]] = {}
            llm_stream = None
            try:
                llm_stream = chat_with_tools_stream(context.messages, tool_defs)
                async for evt in llm_stream:
                    # 协作式取消：在 token 或 tool_call 增量之间检查停止信号。
                    if cancel_event is not None and cancel_event.is_set():
                        yield {"type": "generation_cancelled"}
                        return
                    if evt["type"] == "text":
                        text_parts.append(evt["content"])
                        yield {"type": "text", "content": evt["content"]}
                        continue

                    idx = evt.get("index")
                    if idx is None:
                        idx = 0
                    acc = pending_calls.setdefault(
                        idx, {"id": "", "name": "", "arguments": ""}
                    )
                    if evt.get("id"):
                        acc["id"] = evt["id"]
                    if evt.get("name"):
                        acc["name"] += evt["name"]
                    if evt.get("arguments"):
                        acc["arguments"] += evt["arguments"]
            except Exception:
                logger.exception("LLM 调用失败")
                # 不把上游异常原文、URL 或鉴权信息返回给前端。超时、重试
                # 和熔断的详细原因已经记录在 llm_service 的日志中。
                yield {
                    "type": "error",
                    "message": "AI 服务暂时不可用，请稍后重试",
                }
                return
            finally:
                # 停止生成或正常结束时关闭上游 LLM 网络流。
                if llm_stream is not None:
                    try:
                        await llm_stream.aclose()
                    except Exception:
                        # 关闭失败只记录日志，不能覆盖本轮真正的生成结果
                        # 或取消原因。
                        logger.exception("关闭 Agent LLM 流失败")

            content = "".join(text_parts) or None

            # ---- 2. FINAL: 无 tool_calls → 最终回答（文本已在流式过程中推送）----
            if not pending_calls:
                logger.info("Agent 完成，共 %d 轮", iteration + 1)
                return

            tool_calls = [pending_calls[i] for i in sorted(pending_calls)]
            # 兜底：个别服务只在首帧给 id，缺失时补一个
            for i, tc in enumerate(tool_calls):
                tc["id"] = tc["id"] or f"call_{iteration}_{i}"

            # ---- 3. ACTION: 构造 assistant 消息加入上下文 ----
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"] or "{}",
                        },
                    }
                    for tc in tool_calls
                ],
            }
            context.add_assistant_message(assistant_msg)

            # ---- 4. ACTION + OBSERVATION: 执行每个工具 ----
            for tc in tool_calls:
                if cancel_event is not None and cancel_event.is_set():
                    yield {"type": "generation_cancelled"}
                    return

                tool_name = tc["name"]

                # 解析 LLM 生成的参数
                try:
                    arguments = json.loads(tc["arguments"]) if tc["arguments"] else {}
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
                context.add_tool_result(tc["id"], result.to_content())

        # 超过最大迭代次数
        logger.warning("Agent 达到最大循环次数 %d", MAX_ITERATIONS)
        yield {
            "type": "text",
            "content": "Agent 已达到最大执行轮次限制，请尝试简化任务。",
        }
