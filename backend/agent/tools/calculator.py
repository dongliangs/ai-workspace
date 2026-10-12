# agent/tools/calculator.py
"""
Calculator 工具 —— 执行精确数学计算。
===========================================================================
适配新架构：ToolDefinition (Schema) + handler (Function) 分离。

使用方式（在应用启动时显式注册）：
    from agent.tools.calculator import calculator_definition, calculator_handler
    from agent.registry import registry
    registry.register(calculator_definition, calculator_handler)

安全设计：
    使用 Python ast 模块解析表达式，只允许数值运算和数学函数，
    禁止任意属性访问、调用、赋值等危险操作。
===========================================================================
"""
import ast
import math
import operator
from typing import Any

from agent.schema import ToolDefinition

# 允许的二元运算符
_BIN_OPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# 允许的一元运算符
_UNARY_OPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# 允许的数学常量
_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

# 允许的数学函数
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "pow": pow,
}


def _safe_eval_node(node: ast.AST) -> float:
    """递归安全求值 AST 节点。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的一元运算: {type(node.op).__name__}")
        return op_func(_safe_eval_node(node.operand))

    if isinstance(node, ast.BinOp):
        op_func = _BIN_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的运算: {type(node.op).__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return op_func(left, right)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("不支持的方法调用")
        func = _FUNCTIONS.get(node.func.id)
        if func is None:
            raise ValueError(f"不支持的函数: {node.func.id}")
        args = [_safe_eval_node(arg) for arg in node.args]
        return func(*args)

    raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


# ---- Tool Function (执行函数) ----

async def calculator_handler(expression: str) -> dict[str, Any]:
    """
    执行数学表达式计算。

    Args:
        expression: 数学表达式，如 '2+3*4', '(10-3)/2', 'sqrt(144)+1'

    Returns:
        {"expression": "...", "result": 14}
    """
    expression = expression.strip()
    if not expression:
        raise ValueError("表达式不能为空")

    tree = ast.parse(expression, mode="eval")
    result = _safe_eval_node(tree.body)

    if isinstance(result, float) and result.is_integer():
        result = int(result)

    return {"expression": expression, "result": result}


# ---- Tool Schema (定义) ----

calculator_definition = ToolDefinition(
    name="calculator",
    description=(
        "执行精确数学计算。支持加减乘除、幂运算、取模、括号，"
        "以及 sqrt/log/exp/abs/round/ceil/floor/sin/cos/tan 等数学函数。"
        "输入一个数学表达式字符串，返回计算结果。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2+3*4', '(10-3)/2', 'sqrt(144)+1'",
            }
        },
        "required": ["expression"],
    },
)
