# agent/registry.py
"""
Tool Registry —— 工具注册中心。
===========================================================================
职责：
    管理 ToolDefinition（Schema）与 ToolFunction（执行函数）的绑定关系。

    Agent Runtime 不直接写死具体工具，而是从 Registry 获取：
        - get_definitions() → 传给 LLM 的工具描述列表
        - get_handler()     → 后端执行函数

    以后增加新工具（PDF、数据库查询、知识库搜索）时，
    只需注册新的 ToolDefinition + handler，不需要修改 Agent 核心循环。

架构关系：
    ToolDefinition (schema.py)   ← 纯描述，不含实现
        ↕  绑定
    ToolFunction (handler)        ← 真正干活的异步函数
        ↑
    ToolRegistry.register(definition, handler)
===========================================================================
"""
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from agent.schema import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    """
    工具注册条目：绑定一个 ToolDefinition 和它的执行函数。

    Attributes:
        definition: 工具 Schema（name, description, parameters）
        handler:    异步执行函数，接收关键字参数，返回任意类型数据
    """

    definition: ToolDefinition
    handler: Callable[..., Awaitable[Any]]


class ToolRegistry:
    """
    工具注册表。

    - register():  注册一个工具（Schema + Function）
    - get_definitions(): 返回 OpenAI tools 格式的 Schema 列表，传给 LLM
    - get_handler(): 按名称获取执行函数，供 Executor 调用
    """

    def __init__(self) -> None:
        self._entries: dict[str, ToolEntry] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Awaitable[Any]],
    ) -> None:
        """注册工具：绑定 Schema 和执行函数。"""
        if definition.name in self._entries:
            logger.warning("工具 %s 已注册，将被覆盖", definition.name)
        self._entries[definition.name] = ToolEntry(
            definition=definition,
            handler=handler,
        )

    def get_definition(self, name: str) -> ToolDefinition | None:
        """按名称获取工具 Schema。"""
        entry = self._entries.get(name)
        return entry.definition if entry else None

    def get_handler(self, name: str) -> Callable[..., Awaitable[Any]] | None:
        """按名称获取工具执行函数。"""
        entry = self._entries.get(name)
        return entry.handler if entry else None

    def get_definitions(
        self, names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        返回 OpenAI Chat Completions tools 格式的 Schema 列表。

        Args:
            names: 可选，只返回指定名称的工具；None 表示全部已注册工具。
        """
        entries = self._entries.values()
        if names:
            entries = [e for e in entries if e.definition.name in names]
        return [e.definition.to_openai_format() for e in entries]

    def list_names(self) -> list[str]:
        """返回所有已注册工具的名称。"""
        return list(self._entries.keys())


# 全局工具注册表实例
registry = ToolRegistry()
