# agent/executor.py
"""
Tool Executor —— 工具执行器。
===========================================================================
职责：
    接收 LLM 的 tool_call，从 Registry 查找对应 handler，
    执行并返回结构化 ToolResult。

    无论成功还是失败，executor 始终返回 ToolResult，不抛异常。
    这样 Runtime 的 ReAct 循环不需要 try/except 包裹每次工具调用，
    只需读取 ToolResult.status 判断结果。

    Tool Executor 不关心 Agent Loop 的循环逻辑，只负责：
    1. 按名称查找工具 handler（通过 Registry）
    2. 传入 LLM 生成的参数
    3. 执行并返回 ToolResult（success 或 error）
===========================================================================
"""
import inspect
import logging

from agent.registry import registry
from agent.schema import ToolResult

logger = logging.getLogger(__name__)


def _merge_arguments(handler, arguments: dict, context: dict | None) -> dict:
    """
    合并 LLM 参数与服务端注入的会话上下文。

    - 只注入 handler 签名声明了（或 **kwargs 接收）的上下文键，
      避免把 user_id 等传给不需要它的工具（如 calculator）导致 TypeError
    - 服务端注入值优先于 LLM 参数，防止 LLM 越权伪造（如指定任意 kb_id）
    """
    if not context:
        return arguments
    params = inspect.signature(handler).parameters
    accepts_var_keyword = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if accepts_var_keyword:
        injectable = context
    else:
        injectable = {k: v for k, v in context.items() if k in params}
    return {**arguments, **injectable}


async def execute_tool(
    name: str,
    arguments: dict,
    context: dict | None = None,
) -> ToolResult:
    """
    执行指定工具，返回结构化结果。

    Args:
        name:      工具名称（LLM 返回的 tool_call.function.name）
        arguments: 工具参数（LLM 返回的 JSON 解析后的 dict）
        context:   服务端注入的会话上下文（user_id / kb_id 等），
                   不暴露给 LLM，且不可被 LLM 参数覆盖

    Returns:
        ToolResult: 始终返回，不抛异常。
        - status="success": data 为工具返回的数据
        - status="error":   error 为错误信息
    """
    handler = registry.get_handler(name)
    if handler is None:
        logger.warning("未注册的工具: %s", name)
        return ToolResult.failure(name, f"未注册的工具: {name}")

    merged = _merge_arguments(handler, arguments, context)
    logger.info("执行工具 %s，参数: %s", name, merged)

    try:
        data = await handler(**merged)
        return ToolResult.success(name, data)
    except Exception as e:
        logger.exception("工具 %s 执行异常", name)
        return ToolResult.failure(name, str(e))
