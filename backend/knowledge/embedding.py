"""
Embedding 适配层 —— 基于 LangChain HuggingFaceEmbeddings。
===========================================================================
使用 LangChain Embeddings 接口适配 BAAI/bge-small-zh-v1.5 模型。

设计要点：
    - 通过 langchain-huggingface 的 HuggingFaceEmbeddings 封装
    - 模型单例：整个应用生命周期只加载一次
    - L2 归一化：bge 系列推荐归一化后用内积（等价余弦相似度）
    - 同时提供 LangChain Embeddings 接口 和 原始 list[float] 接口
    - 写入索引和查询必须用同一个模型，模型变更需重建索引

LangChain Embeddings 接口：
    embed_documents(texts) → list[list[float]]  批量向量化
    embed_query(text)      → list[float]        单条查询向量化
===========================================================================
"""
import logging
import os

# 国内访问 huggingface.co 不通，默认走 hf-mirror.com 镜像。
# 必须在 import langchain_huggingface（其内部读 HF_ENDPOINT）之前设置。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 模型已完整缓存到本地后，禁用联网校验（每次加载时的 HEAD 请求），
# 避免 hf-mirror.com 网络波动/超时导致文档向量化报错。
# 全新环境首次下载模型时，可通过环境变量 HF_HUB_OFFLINE=0 覆盖此默认值。
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from langchain_huggingface import HuggingFaceEmbeddings

from core.config import settings

logger = logging.getLogger(__name__)

# ── LangChain Embeddings 单例 ──────────────────────────────

_embeddings: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    获取 LangChain HuggingFaceEmbeddings 单例。

    返回的对象同时满足 LangChain Embeddings 接口和直接调用需求。
    首次调用时下载/加载模型（~95MB）。
    """
    global _embeddings
    if _embeddings is None:
        logger.info("加载 Embedding 模型 (LangChain): %s", settings.embedding_model_name)
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model_name,
            model_kwargs={"device": "cpu"},  # V0.3 先用 CPU，有 GPU 可改为 "cuda"
            encode_kwargs={"normalize_embeddings": True},  # L2 归一化
        )
        logger.info(
            "Embedding 模型加载完成, 维度=%d", settings.embedding_dim
        )
    return _embeddings


# ── 便捷封装（供非 LangChain 调用方使用）──────────────────


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    批量文本向量化（索引构建时使用）。

    内部调用 LangChain Embeddings.embed_documents。
    """
    if not texts:
        return []
    valid_texts = [t.strip() for t in texts if t.strip()]
    if not valid_texts:
        return []
    return get_embeddings().embed_documents(valid_texts)


def embed_query(text: str) -> list[float]:
    """
    单条查询向量化（检索时使用）。

    内部调用 LangChain Embeddings.embed_query。
    """
    return get_embeddings().embed_query(text.strip())
