"""
检索服务 —— 基于 LangChain Retriever 模式。
===========================================================================
职责：
    1. 通过 LangChain VectorStore.similarity_search_with_score 检索
    2. 按相似度阈值过滤无关结果
    3. 返回结构化检索结果（含来源元数据）

不做的事：
    - 不调用 LLM（由 rag_service 负责）
    - 不做权限校验（由上层 service 负责）

LangChain Retriever 链路：
    query → VectorStore.embed_query → Milvus similarity_search → 过滤
===========================================================================
"""
import logging
from typing import Any

from core.config import settings
from knowledge.vector_store import similarity_search

logger = logging.getLogger(__name__)


def retrieve(
    question: str,
    user_id: int,
    kb_id: int,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    检索与问题最相关的知识片段。

    内部调用 LangChain VectorStore 的 similarity_search_with_score，
    VectorStore 自动调用 Embeddings.embed_query 将问题向量化。

    Args:
        question: 用户问题
        user_id:  用户 ID
        kb_id:    知识库 ID
        top_k:    返回条数，默认用配置值

    Returns:
        检索结果列表（按相似度降序），已过滤低于阈值的结果。
        每条含 content / document_id / chunk_index / page_number / score
    """
    results = similarity_search(
        query=question,
        user_id=user_id,
        kb_id=kb_id,
        top_k=top_k or settings.retrieval_top_k,
    )

    # 阈值过滤
    threshold = settings.retrieval_score_threshold
    filtered = [r for r in results if r["score"] >= threshold]

    logger.info(
        "检索完成: question='%s...', kb_id=%d, 原始=%d, 过滤后=%d",
        question[:50], kb_id, len(results), len(filtered),
    )

    return filtered
