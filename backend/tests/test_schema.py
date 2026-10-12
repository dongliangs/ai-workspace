"""
ToolDefinition + ToolResult 单元测试。
"""
import json

from agent.schema import ToolDefinition, ToolResult


# ── ToolDefinition ──────────────────────────────────────────────────

class TestToolDefinition:
    """ToolDefinition Schema 测试"""

    def test_creation(self):
        """工具定义创建：字段正确赋值"""
        td = ToolDefinition(
            name="calculator",
            description="计算器",
            parameters={"type": "object", "properties": {}},
        )
        assert td.name == "calculator"
        assert td.description == "计算器"
        assert td.parameters == {"type": "object", "properties": {}}

    def test_to_openai_format_structure(self):
        """转换为 OpenAI tools 格式：结构正确"""
        td = ToolDefinition(
            name="echo",
            description="回显工具",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        )
        fmt = td.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "echo"
        assert fmt["function"]["description"] == "回显工具"
        assert fmt["function"]["parameters"] == {"type": "object", "properties": {"text": {"type": "string"}}}


# ── ToolResult ──────────────────────────────────────────────────────

class TestToolResult:
    """ToolResult 输出结构测试"""

    def test_success_factory(self):
        """success() 工厂方法：status=success, data 有值"""
        r = ToolResult.success("calculator", {"result": 42})
        assert r.tool == "calculator"
        assert r.status == "success"
        assert r.data == {"result": 42}
        assert r.error is None

    def test_failure_factory(self):
        """failure() 工厂方法：status=error, error 有值"""
        r = ToolResult.failure("calculator", "表达式无效")
        assert r.tool == "calculator"
        assert r.status == "error"
        assert r.error == "表达式无效"
        assert r.data is None

    def test_to_content_success(self):
        """to_content() 成功时返回 JSON 字符串"""
        r = ToolResult.success("calc", {"result": 14})
        content = r.to_content()
        assert json.loads(content) == {"result": 14}

    def test_to_content_success_with_chinese(self):
        """to_content() 成功时确保中文不被转义"""
        r = ToolResult.success("calc", {"msg": "计算完成"})
        content = r.to_content()
        assert "计算完成" in content

    def test_to_content_error(self):
        """to_content() 失败时返回错误说明字符串"""
        r = ToolResult.failure("calc", "除以零")
        content = r.to_content()
        assert "工具执行失败" in content
        assert "除以零" in content

    def test_to_dict(self):
        """to_dict() 返回完整字段"""
        r = ToolResult.success("calc", {"result": 1})
        d = r.to_dict()
        assert d["tool"] == "calc"
        assert d["status"] == "success"
        assert d["data"] == {"result": 1}
        assert d["error"] is None

    def test_to_dict_error(self):
        """to_dict() 错误结果"""
        r = ToolResult.failure("calc", "失败原因")
        d = r.to_dict()
        assert d["status"] == "error"
        assert d["error"] == "失败原因"
        assert d["data"] is None
