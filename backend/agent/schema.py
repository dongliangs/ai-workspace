# agent/schema.py
"""
Tool Schema 层 —— 工具的输入与输出定义。
===========================================================================
三层分离设计：

    1. ToolDefinition (Schema)
       告诉 LLM：工具叫什么、能做什么、需要什么参数、什么时候调用。
       纯数据，不含执行逻辑。

    2. ToolFunction (执行函数)
       真正干活的 Python 异步函数，如读取 Excel、计算销售额。
       在 Registry 中与 ToolDefinition 绑定，Schema 不关心它怎么实现。

    3. ToolResult (输出结构)
       工具执行后返回给 Agent 的结构化数据。
       Agent（LLM）拿到结果后可以选择：继续调用工具，或生成最终回答。

设计原则：
    - Schema 和 Function 分离：同一个 Schema 可以对接不同的实现
      （例如 analyze_excel 可以是 pandas 实现也可以是 openpyxl 实现）
    - ToolResult 统一格式：无论成功还是失败，executor 始终返回 ToolResult，
      由 to_content() 转换为 LLM 可读字符串，追加到上下文。
===========================================================================
"""
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    """
    工具定义 Schema —— 告诉 LLM 工具能做什么。

    这部分纯描述性数据，会被转换为 OpenAI tools 格式传给模型。
    模型据此判断：什么时候该调用这个工具、调用时传什么参数。

    Attributes:
        name:        工具唯一标识，LLM 调用时使用此名称。
        description: 工具描述，LLM 据此判断什么时候应该调用。
        parameters:  JSON Schema dict，描述工具接受的参数结构。
    """

    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_format(self) -> dict[str, Any]:
        """转换为 OpenAI Chat Completions tools 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult:
    """
    工具执行结果 —— 返回数据给 Agent。

    无论成功还是失败，executor 始终返回 ToolResult。
    Agent（LLM）拿到结果后决定下一步：
        - 继续调用其他工具
        - 基于已有结果生成最终回答

    Attributes:
        tool:   工具名称
        status: 执行状态 "success" | "error"
        data:   成功时的返回数据（任意类型）
        error:  失败时的错误信息
    """

    def __init__(
        self,
        tool: str,
        status: str,
        data: Any = None,
        error: str | None = None,
    ) -> None:
        self.tool = tool
        self.status = status
        self.data = data
        self.error = error

    @classmethod
    def success(cls, tool: str, data: Any) -> "ToolResult":
        """创建成功结果。"""
        return cls(tool=tool, status="success", data=data)

    @classmethod
    def failure(cls, tool: str, error: str) -> "ToolResult":
        """创建失败结果。"""
        return cls(tool=tool, status="error", error=error)

    def to_content(self) -> str:
        """
        转换为 LLM tool message 的 content 字符串。

        LLM 通过这个字符串理解工具执行了什么、返回了什么数据。
        成功时序列化 data，失败时返回错误说明。
        """
        if self.status == "success":
            return json.dumps(self.data, ensure_ascii=False)
        return f"工具执行失败: {self.error}"

    def to_dict(self) -> dict[str, Any]:
        """转换为普通 dict（用于 SSE 事件序列化）。"""
        return {
            "tool": self.tool,
            "status": self.status,
            "data": self.data,
            "error": self.error,
        }
