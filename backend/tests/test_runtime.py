"""
AgentContext + AgentRuntime (ReAct 循环) 单元测试。

使用 mock LLM 响应，不依赖真实 AI 服务。
"""
import asyncio
from unittest.mock import AsyncMock, patch

from agent.runtime import AgentContext, AgentRuntime
from agent.registry import ToolRegistry
from agent.schema import ToolDefinition
from tests.conftest import (
    MockToolCall,
    make_text_response,
    make_tool_call_response,
)


# ── AgentContext 测试 ────────────────────────────────────────────────

class TestAgentContext:
    """Agent 上下文消息管理测试"""

    def test_init_with_system_prompt(self):
        ctx = AgentContext("你是 Agent")
        assert ctx.messages[0] == {"role": "system", "content": "你是 Agent"}

    def test_init_without_system_prompt(self):
        ctx = AgentContext("")
        assert len(ctx.messages) == 0

    def test_add_user_message(self):
        ctx = AgentContext("sys")
        ctx.add_user_message("你好")
        assert ctx.messages[-1] == {"role": "user", "content": "你好"}

    def test_add_history(self):
        ctx = AgentContext("sys")
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]
        ctx.add_history(history)
        assert len(ctx.messages) == 3  # system + 2 history
        assert ctx.messages[1] == {"role": "user", "content": "之前的问题"}

    def test_add_assistant_message(self):
        ctx = AgentContext("sys")
        msg = {"role": "assistant", "content": "回答", "tool_calls": []}
        ctx.add_assistant_message(msg)
        assert ctx.messages[-1]["role"] == "assistant"

    def test_add_tool_result(self):
        ctx = AgentContext("sys")
        ctx.add_tool_result("call_123", "结果数据")
        assert ctx.messages[-1] == {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": "结果数据",
        }

    def test_full_context_assembly(self):
        """完整上下文组装顺序：system → history → user"""
        ctx = AgentContext("system_prompt")
        ctx.add_history([{"role": "user", "content": "历史问题"}])
        ctx.add_user_message("当前问题")
        assert len(ctx.messages) == 3
        assert ctx.messages[0]["role"] == "system"
        assert ctx.messages[1]["content"] == "历史问题"
        assert ctx.messages[2]["content"] == "当前问题"


# ── AgentRuntime ReAct 循环测试 ──────────────────────────────────────

class TestAgentRuntimeNoTools:
    """无工具时 ReAct 循环退化为普通对话"""

    async def test_no_tools_text_only(self):
        """无工具注册：LLM 返回纯文本 → agent_start + text → 结束"""
        reg = ToolRegistry()
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("你好")

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = make_text_response("你好，我是 Agent")
            events = [e async for e in runtime.run(ctx)]

        # 事件：agent_start → text → 结束（done 由 service 发）
        assert events[0] == {"type": "agent_start"}
        assert events[1] == {"type": "text", "content": "你好，我是 Agent"}
        assert len(events) == 2  # 没有更多事件

        # LLM 只被调用一次
        assert mock_llm.call_count == 1
        # 传给 LLM 的 tools 参数为空列表（第二个位置参数）
        tools_arg = mock_llm.call_args.args[1]
        assert tools_arg == []


class TestAgentRuntimeWithTools:
    """有工具时 ReAct 循环：Thought → Action → Observation → Final"""

    async def test_single_tool_call_then_final(self, echo_definition, echo_handler):
        """单轮工具调用：LLM 先返回 tool_call → 执行 → 再返回文本"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("请回显 hello")

        # 第一次调用：返回 tool_call
        # 第二次调用：返回最终文本
        responses = [
            make_tool_call_response(
                "我先调用 echo 工具",
                [MockToolCall("call_1", "echo", {"text": "hello"})],
            ),
            make_text_response("回显结果：hello"),
        ]

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm, \
             patch("agent.executor.registry", reg):
            mock_llm.side_effect = responses
            events = [e async for e in runtime.run(ctx)]

        # 事件流：
        # 1. agent_start
        # 2. text "我先调用 echo 工具"  (Thought)
        # 3. tool_start  (Action)
        # 4. tool_result  (Observation)
        # 5. text "回显结果：hello"  (Final)
        assert events[0] == {"type": "agent_start"}
        assert events[1]["type"] == "text"
        assert "echo" in events[1]["content"]

        assert events[2] == {
            "type": "tool_start",
            "tool": "echo",
            "arguments": {"text": "hello"},
        }

        assert events[3]["type"] == "tool_result"
        assert events[3]["tool"] == "echo"
        assert events[3]["status"] == "success"

        assert events[4]["type"] == "text"
        assert events[4]["content"] == "回显结果：hello"

        assert len(events) == 5

        # LLM 被调用两次
        assert mock_llm.call_count == 2

        # 上下文最终包含 tool 消息
        roles = [m["role"] for m in ctx.messages]
        assert "tool" in roles

    async def test_tool_error_handling(self, failing_definition, failing_handler):
        """工具执行失败：返回 error ToolResult，循环继续"""
        reg = ToolRegistry()
        reg.register(failing_definition, failing_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("触发失败")

        responses = [
            make_tool_call_response(
                None,
                [MockToolCall("call_1", "boom", {})],
            ),
            make_text_response("工具执行失败了，我换个方法"),
        ]

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm, \
             patch("agent.executor.registry", reg):
            mock_llm.side_effect = responses
            events = [e async for e in runtime.run(ctx)]

        # tool_result 事件应为 error 状态
        tool_result_event = [e for e in events if e["type"] == "tool_result"][0]
        assert tool_result_event["status"] == "error"
        assert "工具内部错误" in tool_result_event["result"]

        # 循环继续，最终有文本回答
        assert events[-1]["type"] == "text"

    async def test_llm_error(self, echo_definition, echo_handler):
        """LLM 调用失败：推送错误文本，结束循环"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("test")

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = ConnectionError("网络错误")
            events = [e async for e in runtime.run(ctx)]

        assert events[0] == {"type": "agent_start"}
        assert events[1]["type"] == "text"
        assert "AI 服务" in events[1]["content"]
        assert len(events) == 2  # 结束

    async def test_max_iterations(self, echo_definition, echo_handler):
        """超过最大循环次数：LLM 始终返回 tool_call → 达到上限后停止"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("无限循环")

        # 每次都返回 tool_call，永不返回纯文本
        response = make_tool_call_response(
            "继续",
            [MockToolCall("call_x", "echo", {"text": "loop"})],
        )

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = response
            events = [e async for e in runtime.run(ctx)]

        # 最后一条事件应提示达到最大轮次
        assert events[-1]["type"] == "text"
        assert "最大执行轮次" in events[-1]["content"]

        # LLM 被调用 MAX_ITERATIONS 次
        from agent.runtime import MAX_ITERATIONS
        assert mock_llm.call_count == MAX_ITERATIONS

    async def test_context_grows_with_tool_results(self, echo_definition, echo_handler):
        """工具结果正确加入上下文：第二轮 LLM 能看到 tool 消息"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("回显 test")

        responses = [
            make_tool_call_response(
                None,
                [MockToolCall("c1", "echo", {"text": "test"})],
            ),
            make_text_response("done"),
        ]

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm, \
             patch("agent.executor.registry", reg):
            mock_llm.side_effect = responses
            _ = [e async for e in runtime.run(ctx)]

        # 第二次调用时，messages 应包含 tool 角色消息
        second_call_messages = mock_llm.call_args_list[1].args[0]
        roles = [m["role"] for m in second_call_messages]
        assert "tool" in roles
        assert "assistant" in roles

    async def test_tool_names_filter(self, echo_definition, echo_handler):
        """tool_names 参数：只传指定工具给 LLM"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)

        # 再注册一个工具
        td2 = ToolDefinition("other", "其他工具", {"type": "object", "properties": {}})

        async def h2(**kw):
            pass

        reg.register(td2, h2)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("test")

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm, \
             patch("agent.executor.registry", reg):
            mock_llm.return_value = make_text_response("done")
            _ = [e async for e in runtime.run(ctx, tool_names=["echo"])]

        # 传给 LLM 的 tools 只应包含 echo（第二个位置参数）
        tools = mock_llm.call_args.args[1]
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "echo"

    async def test_multiple_tool_calls_in_one_response(self, echo_definition, echo_handler):
        """一轮中多个 tool_call：全部执行后再进入下一轮"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        runtime = AgentRuntime(reg)

        ctx = AgentContext("sys")
        ctx.add_user_message("回显多个")

        responses = [
            make_tool_call_response(
                "调用两次 echo",
                [
                    MockToolCall("c1", "echo", {"text": "a"}),
                    MockToolCall("c2", "echo", {"text": "b"}),
                ],
            ),
            make_text_response("两个都回显了"),
        ]

        with patch("agent.runtime.chat_with_tools", new_callable=AsyncMock) as mock_llm, \
             patch("agent.executor.registry", reg):
            mock_llm.side_effect = responses
            events = [e async for e in runtime.run(ctx)]

        # 应有 2 个 tool_start 和 2 个 tool_result
        tool_starts = [e for e in events if e["type"] == "tool_start"]
        tool_results = [e for e in events if e["type"] == "tool_result"]
        assert len(tool_starts) == 2
        assert len(tool_results) == 2
