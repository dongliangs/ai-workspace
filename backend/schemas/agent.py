# schemas/agent.py
"""
Agent 消息请求 Schema。
===========================================================================
对应 POST /agent/{conversation_id}/messages 接口的请求体。
===========================================================================
"""
from pydantic import BaseModel


class AgentMessageCreate(BaseModel):
    """Agent 消息请求体。"""

    # 用户输入文本
    content: str
    # 携带的文件 id 列表（可选），供 Agent 工具调用
    file_ids: list[int] | None = None
    # 指定使用的工具列表（可选，不传则由 Agent 自行决定使用全部已注册工具）
    tools: list[str] | None = None
    # 绑定的知识库 id（可选）：绑定后 Agent 可调用 knowledge_search 检索该知识库，
    # 由服务端校验归属并注入，LLM 无法伪造
    kb_id: int | None = None
