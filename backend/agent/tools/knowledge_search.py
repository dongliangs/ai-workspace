"""
Knowledge Search 工具 —— Agent 调用知识库检索。
===========================================================================
作为 V0.2 Agent Runtime 的工具，供 LLM 在对话中按需调用。

工作方式：
    1. LLM 决定调用 knowledge_search，传入 question 参数
    2. Executor 调用本 handler，并从会话上下文注入 user_id 和 kb_id
    3. handler 调用 retrieval.retrieve() 检索知识片段
    4. 返回原始数据 dict，由 Executor 统一包装为 ToolResult

契约（与其他工具一致）：
    - handler 只返回原始数据（dict），不构造 ToolResult
    - 检索异常直接抛出，由 Executor 捕获并转为 error 结果

安全规则：
    - user_id 和 kb_id 由 Executor 从会话上下文注入，LLM 不能指定
    - 如果当前会话没有绑定知识库，工具返回提示而非搜索全部文档
===========================================================================
"""
import logging
from typing import Any

from agent.schema import ToolDefinition
from knowledge.retrieval import retrieve

logger = logging.getLogger(__name__)


async def knowledge_search_handler(
    question: str,
    user_id: int = 0,
    kb_id: int = 0,
    **kwargs: Any,
) -> dict:
    """
    知识库检索工具 handler。

    注意：user_id 和 kb_id 由 Executor 从会话上下文注入，
    不在 LLM 参数中暴露。如果 kb_id 为 0，表示当前会话未绑定知识库。

    Args:
        question: 搜索问题
        user_id:  用户 ID（服务端注入）
        kb_id:    知识库 ID（服务端注入）

    Returns:
        dict: 检索结果（含片段列表摘要），由 Executor 包装为 ToolResult
    """
    if not kb_id:
        return {
            "found": False,
            "message": "当前会话未绑定知识库，无法检索。请先选择知识库。",
        }

    # 异常直接抛出，由 Executor 捕获并转为 ToolResult.failure
    chunks = retrieve(
        question=question,
        user_id=user_id,
        kb_id=kb_id,
    )

    if not chunks:
        return {
            "found": False,
            "message": "未在知识库中找到与问题相关的片段。",
            "question": question,
        }

    # 组装检索片段摘要（传给 LLM，不需要完整向量数据）
    fragments = []
    for i, chunk in enumerate(chunks, 1):
        fragments.append({
            "index": i,
            "content": chunk["content"][:500],  # 截断防 token 过长
            "document_id": chunk["document_id"],
            "page_number": chunk.get("page_number", -1),
            "score": round(chunk.get("score", 0.0), 4),
        })

    return {
        "found": True,
        "question": question,
        "fragment_count": len(fragments),
        "fragments": fragments,
    }


# ── 工具定义 ──────────────────────────────────────────────

knowledge_search_definition = ToolDefinition(
    name="knowledge_search",
    description=(
        "在用户绑定的知识库中检索与问题相关的文档片段。"
        "当用户提问涉及已上传的知识库文档内容时调用此工具。"
        "传入用户的问题，工具返回检索到的相关文本片段和来源信息。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "要检索的问题或关键词",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
)
