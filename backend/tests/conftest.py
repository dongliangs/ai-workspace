"""
共享 fixtures 和 mock 工具。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 确保能 import backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.schema import ToolDefinition


# ── Mock LLM 响应构造器 ──────────────────────────────────────────────

class MockFunction:
    """模拟 OpenAI tool_call.function"""
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    """模拟 OpenAI ChatCompletionMessageToolCall"""
    def __init__(self, id: str, name: str, arguments: dict):
        self.id = id
        self.type = "function"
        import json
        self.function = MockFunction(name, json.dumps(arguments))


class MockMessage:
    """模拟 OpenAI ChatCompletionMessage"""
    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls


class MockChoice:
    """模拟 OpenAI Choice"""
    def __init__(self, message: MockMessage):
        self.message = message


class MockResponse:
    """模拟 OpenAI ChatCompletion 响应"""
    def __init__(self, message: MockMessage):
        self.choices = [MockChoice(message)]


def make_text_response(text: str) -> MockResponse:
    """构造一个纯文本响应（无 tool_calls）→ 最终答案"""
    return MockResponse(MockMessage(content=text, tool_calls=None))


def make_tool_call_response(
    content: str | None,
    tool_calls: list[MockToolCall],
) -> MockResponse:
    """构造一个带 tool_calls 的响应"""
    return MockResponse(MockMessage(content=content, tool_calls=tool_calls))


# ── 测试用工具定义和 handler ─────────────────────────────────────────

@pytest.fixture
def echo_definition():
    """一个简单的 echo 工具定义，用于测试"""
    return ToolDefinition(
        name="echo",
        description="原样返回输入内容",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要回显的文本"}
            },
            "required": ["text"],
        },
    )


@pytest.fixture
def echo_handler():
    """echo 工具的执行函数"""
    async def _handler(text: str) -> dict:
        return {"echoed": text}
    return _handler


@pytest.fixture
def failing_handler():
    """一个总是抛异常的 handler，用于测试错误处理"""
    async def _handler(**kwargs):
        raise RuntimeError("工具内部错误")
    return _handler


@pytest.fixture
def failing_definition():
    """一个总是失败的工具定义"""
    return ToolDefinition(
        name="boom",
        description="这个工具总是会失败",
        parameters={"type": "object", "properties": {}},
    )
