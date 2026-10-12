"""
Calculator 工具 handler 单元测试。
"""
import asyncio

import pytest

from agent.tools.calculator import calculator_handler


class TestCalculatorBasic:
    """基础运算测试"""

    @pytest.mark.parametrize("expr, expected", [
        ("2+3", 5),
        ("10-4", 6),
        ("3*4", 12),
        ("15/3", 5),
        ("7//2", 3),
        ("7%3", 1),
        ("2**10", 1024),
    ])
    def test_basic_operations(self, expr, expected):
        result = asyncio.run(calculator_handler(expression=expr))
        assert result["result"] == expected
        assert result["expression"] == expr

    def test_operator_precedence(self):
        """运算符优先级：乘法先于加法"""
        result = asyncio.run(calculator_handler(expression="2+3*4"))
        assert result["result"] == 14

    def test_parentheses(self):
        """括号改变优先级"""
        result = asyncio.run(calculator_handler(expression="(2+3)*4"))
        assert result["result"] == 20

    def test_nested_parentheses(self):
        """嵌套括号"""
        result = asyncio.run(calculator_handler(expression="((1+2)*(3+4))"))
        assert result["result"] == 21


class TestCalculatorFunctions:
    """数学函数测试"""

    @pytest.mark.parametrize("expr, expected", [
        ("sqrt(144)", 12),
        ("abs(-5)", 5),
        ("round(3.7)", 4),
        ("ceil(3.2)", 4),
        ("floor(3.8)", 3),
        ("exp(0)", 1),
        ("log(e)", 1),
    ])
    def test_math_functions(self, expr, expected):
        result = asyncio.run(calculator_handler(expression=expr))
        # 浮点比较
        assert abs(result["result"] - expected) < 1e-9

    def test_trig_functions(self):
        """三角函数"""
        result = asyncio.run(calculator_handler(expression="sin(0)"))
        assert abs(result["result"]) < 1e-9

    def test_multiple_functions(self):
        """复合函数调用"""
        result = asyncio.run(calculator_handler(expression="sqrt(144)+abs(-3)"))
        assert result["result"] == 15

    def test_constants(self):
        """数学常量"""
        result = asyncio.run(calculator_handler(expression="pi"))
        assert abs(result["result"] - 3.141592653589793) < 1e-9


class TestCalculatorEdgeCases:
    """边界与异常情况"""

    def test_integer_result_no_decimal(self):
        """整数结果应为 int 而非 float"""
        result = asyncio.run(calculator_handler(expression="4/2"))
        assert result["result"] == 2
        assert isinstance(result["result"], int)

    def test_float_result(self):
        """非整数结果保留 float"""
        result = asyncio.run(calculator_handler(expression="7/2"))
        assert result["result"] == 3.5

    def test_empty_expression(self):
        """空表达式：抛 ValueError"""
        with pytest.raises(ValueError, match="不能为空"):
            asyncio.run(calculator_handler(expression=""))

    def test_whitespace_expression(self):
        """纯空白表达式：抛 ValueError"""
        with pytest.raises(ValueError, match="不能为空"):
            asyncio.run(calculator_handler(expression="   "))

    def test_division_by_zero(self):
        """除以零：抛 ZeroDivisionError"""
        with pytest.raises(ZeroDivisionError):
            asyncio.run(calculator_handler(expression="1/0"))

    def test_unsupported_syntax(self):
        """不支持的语法（变量赋值）：抛异常"""
        with pytest.raises(Exception):
            asyncio.run(calculator_handler(expression="x=1"))

    def test_unsupported_function(self):
        """不支持的函数：抛 ValueError"""
        with pytest.raises(ValueError, match="不支持的函数"):
            asyncio.run(calculator_handler(expression="exec('code')"))

    def test_complex_expression(self):
        """复合表达式"""
        result = asyncio.run(calculator_handler(expression="(2+3)*sqrt(16)-1"))
        assert result["result"] == 19
