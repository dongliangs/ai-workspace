"""
Tool Executor 单元测试。
"""
import asyncio

from agent.executor import execute_tool
from agent.registry import ToolRegistry, registry
from agent.schema import ToolResult


class TestExecuteTool:
    """execute_tool 执行器测试"""

    def test_success(self, echo_definition, echo_handler):
        """正常执行：返回 success ToolResult"""
        # 用独立 registry 实例，避免全局污染
        import agent.executor as exec_mod
        original = exec_mod.registry
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        exec_mod.registry = reg

        try:
            result = asyncio.run(execute_tool("echo", {"text": "hello"}))
            assert isinstance(result, ToolResult)
            assert result.status == "success"
            assert result.tool == "echo"
            assert result.data == {"echoed": "hello"}
            assert result.error is None
        finally:
            exec_mod.registry = original

    def test_unregistered_tool(self):
        """调用未注册工具：返回 error ToolResult，不抛异常"""
        import agent.executor as exec_mod
        original = exec_mod.registry
        reg = ToolRegistry()
        exec_mod.registry = reg

        try:
            result = asyncio.run(execute_tool("nonexistent", {}))
            assert result.status == "error"
            assert "未注册" in result.error
        finally:
            exec_mod.registry = original

    def test_handler_exception(self, failing_definition, failing_handler):
        """handler 抛异常：返回 error ToolResult，不向上传播"""
        import agent.executor as exec_mod
        original = exec_mod.registry
        reg = ToolRegistry()
        reg.register(failing_definition, failing_handler)
        exec_mod.registry = reg

        try:
            result = asyncio.run(execute_tool("boom", {}))
            assert result.status == "error"
            assert "工具内部错误" in result.error
        finally:
            exec_mod.registry = original

    def test_result_is_toolresult(self, echo_definition, echo_handler):
        """返回值始终是 ToolResult 实例"""
        import agent.executor as exec_mod
        original = exec_mod.registry
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        exec_mod.registry = reg

        try:
            result = asyncio.run(execute_tool("echo", {"text": "test"}))
            assert isinstance(result, ToolResult)
        finally:
            exec_mod.registry = original

    def test_to_content_after_success(self, echo_definition, echo_handler):
        """成功结果的 to_content() 可被 JSON 解析"""
        import agent.executor as exec_mod
        original = exec_mod.registry
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        exec_mod.registry = reg

        try:
            import json
            result = asyncio.run(execute_tool("echo", {"text": "hi"}))
            content = result.to_content()
            parsed = json.loads(content)
            assert parsed == {"echoed": "hi"}
        finally:
            exec_mod.registry = original
