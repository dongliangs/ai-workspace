"""
向量存储适配层 —— 基于 LangChain Milvus 集成。
===========================================================================
使用 langchain-milvus 的 Milvus 类封装 Milvus-lite（本地嵌入式）。

LangChain VectorStore 接口：
    add_documents(docs)                             → 写入（自动向量化）
    similarity_search_with_score(query, k, expr)    → 检索（自动向量化 + metadata filter）

删除操作（pymilvus 直接调用，LangChain 不支持 expr 删除）：
    delete_by_document(document_id)
    delete_by_knowledge_base(kb_id)
===========================================================================
"""
import logging
from typing import Any

from langchain_core.documents import Document
from langchain_milvus import Milvus
from pymilvus import MilvusClient

from core.config import settings
from knowledge.embedding import get_embeddings

logger = logging.getLogger(__name__)

_vector_store: Milvus | None = None
_pymilvus_client: MilvusClient | None = None


class _LazyEmbeddings:
    """
    延迟加载的 Embeddings 代理。

    实现 LangChain Embeddings 接口，首次实际调用 embed_* 时才加载模型。
    传给 Milvus 构造函数，避免应用启动（init_collection）时触发模型下载。
    模型（~95MB）在第一次上传文档或检索时才从 HF 镜像加载。
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return get_embeddings().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return get_embeddings().embed_query(text)


def get_vector_store() -> Milvus:
    """获取 LangChain Milvus VectorStore 单例。"""
    global _vector_store
    if _vector_store is None:
        logger.info("初始化 LangChain Milvus, db=%s", settings.milvus_db_path)
        _vector_store = Milvus(
            embedding_function=_LazyEmbeddings(),
            collection_name=settings.milvus_collection_name,
            connection_args={"uri": settings.milvus_db_path},
            auto_id=True,
            index_params={
                "metric_type": "IP",
                "index_type": "FLAT",
            },
        )
        logger.info("LangChain Milvus VectorStore 初始化完成")
    return _vector_store


def _get_pymilvus_client() -> MilvusClient:
    """获取 pymilvus 客户端单例（用于 expr 删除操作）。"""
    global _pymilvus_client
    if _pymilvus_client is None:
        _pymilvus_client = MilvusClient(settings.milvus_db_path)
    return _pymilvus_client


def init_collection() -> None:
    """初始化 collection（获取 VectorStore 实例，集合在首次写入时自动创建）。"""
    get_vector_store()


def add_documents(docs: list[Document]) -> int:
    """
    批量写入 LangChain Document 到向量库（自动向量化）。

    每个 Document 的 page_content 为文本内容，
    metadata 中的 user_id/kb_id/document_id 用于过滤和删除。

    Returns:
        写入条数
    """
    if not docs:
        return 0
    get_vector_store().add_documents(docs)
    logger.info("写入 %d 条向量", len(docs))
    return len(docs)


def similarity_search(
    query: str,
    user_id: int,
    kb_id: int,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    相似度检索（LangChain 自动向量化 + expr filter）。

    Args:
        query:   用户查询文本（VectorStore 自动调 embed_query 向量化）
        user_id: 用户 ID（权限过滤）
        kb_id:   知识库 ID（范围过滤）
        top_k:   返回条数

    Returns:
        检索结果列表，每条含 content / document_id / chunk_index / page_number / score
    """
    k = top_k or settings.retrieval_top_k
    expr = f"user_id == {user_id} and kb_id == {kb_id}"

    results = get_vector_store().similarity_search_with_score(
        query, k=k, expr=expr
    )

    output = []
    for doc, score in results:
        output.append({
            "content": doc.page_content,
            "document_id": doc.metadata.get("document_id", 0),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "page_number": doc.metadata.get("page_number", -1),
            "score": float(score),
        })

    return output


def delete_by_document(document_id: int) -> None:
    """删除指定文档的所有向量（pymilvus expr 删除）。"""
    _get_pymilvus_client().delete(
        collection_name=settings.milvus_collection_name,
        filter=f"document_id == {document_id}",
    )
    logger.info("已删除 document_id=%d 的所有向量", document_id)


def delete_by_knowledge_base(kb_id: int) -> None:
    """删除指定知识库的所有向量（级联删除）。"""
    _get_pymilvus_client().delete(
        collection_name=settings.milvus_collection_name,
        filter=f"kb_id == {kb_id}",
    )
    logger.info("已删除 kb_id=%d 的所有向量", kb_id)
