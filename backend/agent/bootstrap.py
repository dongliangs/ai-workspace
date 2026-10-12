# agent/bootstrap.py
"""
Agent 工具引导（Bootstrap）—— 在应用启动时注册所有工具。
===========================================================================
职责：
    集中管理 Agent 可用工具的注册。
    在 main.py 的 lifespan 中调用 register_all_tools()，
    将所有 ToolDefinition + handler 绑定到全局 registry。

为什么单独放这里：
    - 工具注册是"应用启动时的一次性配置"，不应散落在各模块 __init__.py
    - 集中注册便于查看当前 Agent 可用哪些工具
    - 后续增加 analyze_excel / generate_chart 等工具时，只需在此追加一行
===========================================================================
"""
import logging

from agent.registry import registry
from agent.tools.calculator import calculator_definition, calculator_handler
from agent.tools.analyze_excel import analyze_excel_definition, analyze_excel_handler
from agent.tools.generate_chart import generate_chart_definition, generate_chart_handler

logger = logging.getLogger(__name__)


def register_all_tools() -> None:
    """
    注册所有 Agent 可用工具到全局 registry。

    在应用启动时调用一次。
    """
    registry.register(calculator_definition, calculator_handler)
    registry.register(analyze_excel_definition, analyze_excel_handler)
    registry.register(generate_chart_definition, generate_chart_handler)
    logger.info("已注册工具: %s", registry.list_names())
