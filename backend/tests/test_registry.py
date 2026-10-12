"""
ToolRegistry 单元测试。
"""
from agent.registry import ToolRegistry
from agent.schema import ToolDefinition


class TestToolRegistry:
    """ToolRegistry 注册、查询、导出测试"""

    def test_empty_registry(self):
        """空注册表：list_names 为空，get_definitions 返回空列表"""
        reg = ToolRegistry()
        assert reg.list_names() == []
        assert reg.get_definitions() == []

    def test_register_and_get_definition(self, echo_definition):
        """注册后可按名获取 ToolDefinition"""
        reg = ToolRegistry()

        async def handler(**kw):
            pass

        reg.register(echo_definition, handler)
        td = reg.get_definition("echo")
        assert td is not None
        assert td.name == "echo"

    def test_register_and_get_handler(self, echo_definition, echo_handler):
        """注册后可按名获取 handler"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        h = reg.get_handler("echo")
        assert h is echo_handler

    def test_get_definition_not_found(self):
        """查询不存在的工具：返回 None"""
        reg = ToolRegistry()
        assert reg.get_definition("nope") is None

    def test_get_handler_not_found(self):
        """获取不存在的 handler：返回 None"""
        reg = ToolRegistry()
        assert reg.get_handler("nope") is None

    def test_get_definitions_all(self, echo_definition, echo_handler):
        """get_definitions() 返回全部已注册工具的 OpenAI 格式"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        defs = reg.get_definitions()
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "echo"

    def test_get_definitions_filtered(self, echo_definition, echo_handler):
        """get_definitions(names=...) 只返回指定名称的工具"""
        reg = ToolRegistry()

        async def handler2(**kw):
            pass

        td2 = ToolDefinition("other", "其他", {"type": "object", "properties": {}})
        reg.register(echo_definition, echo_handler)
        reg.register(td2, handler2)

        defs = reg.get_definitions(names=["echo"])
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "echo"

    def test_get_definitions_nonexistent_filter(self, echo_definition, echo_handler):
        """get_definitions(names=...) 过滤不存在的名称：返回空列表"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        defs = reg.get_definitions(names=["nonexistent"])
        assert defs == []

    def test_register_overwrite(self, echo_definition, echo_handler):
        """重复注册同名工具：覆盖旧值，不报错"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)

        async def new_handler(**kw):
            pass

        reg.register(echo_definition, new_handler)
        assert reg.get_handler("echo") is new_handler

    def test_list_names_multiple(self, echo_definition, echo_handler):
        """list_names() 返回所有工具名"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        td2 = ToolDefinition("calc", "计算器", {"type": "object", "properties": {}})

        async def h2(**kw):
            pass

        reg.register(td2, h2)
        assert set(reg.list_names()) == {"echo", "calc"}

    def test_definitions_are_openai_format(self, echo_definition, echo_handler):
        """导出格式符合 OpenAI tools 结构"""
        reg = ToolRegistry()
        reg.register(echo_definition, echo_handler)
        fmt = reg.get_definitions()[0]
        assert fmt["type"] == "function"
        assert "name" in fmt["function"]
        assert "description" in fmt["function"]
        assert "parameters" in fmt["function"]
