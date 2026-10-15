"""
文本切分器 —— 基于 LangChain RecursiveCharacterTextSplitter。
===========================================================================
使用 langchain-text-splitters 的 RecursiveCharacterTextSplitter，
通过 tiktoken 进行 token 计数，适配中文分块。

设计要点：
    - 优先按段落/换行自然切分，超长段落二次切分
    - chunk_size 约 600 tokens，overlap 约 100 tokens
    - 保留来源 metadata（page_number 等）
    - 追加 chunk_index 到每个 chunk 的 metadata

LangChain Document 流转：
    输入: list[Document]（来自 loaders.py，含 page_number metadata）
    输出: list[Document]（追加 chunk_index metadata）
===========================================================================
"""
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings

logger = logging.getLogger(__name__)

# ── Splitter 单例 ──────────────────────────────────────────

_splitter: RecursiveCharacterTextSplitter | None = None


def get_splitter() -> RecursiveCharacterTextSplitter:
    """
    获取 Text Splitter 单例。

    使用 tiktoken (cl100k_base) 进行 token 计数，
    分隔符优先级：段落 > 换行 > 中文句号 > 中文标点 > 空格
    """
    global _splitter
    if _splitter is None:
        _splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4o",  # 使用 gpt-4o 的 tokenizer 近似计数
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=[
                "\n\n",  # 段落
                "\n",    # 换行
                "。",    # 中文句号
                "！",    # 中文感叹号
                "？",    # 中文问号
                "；",    # 中文分号
                ". ",    # 英文句号
                "! ",
                "? ",
                " ",     # 空格
                "",      # 字符级（最后兜底）
            ],
        )
        logger.info(
            "Text Splitter 初始化, chunk_size=%d, overlap=%d",
            settings.chunk_size, settings.chunk_overlap,
        )
    return _splitter


def split_documents(docs: list[Document]) -> list[Document]:
    """
    切分 LangChain Document 列表。

    保留原始 metadata（如 page_number），追加 chunk_index。

    Args:
        docs: loaders 返回的 Document 列表

    Returns:
        切分后的 Document 列表，每个 chunk 含 chunk_index metadata
    """
    if not docs:
        return []

    splitter = get_splitter()
    chunks = splitter.split_documents(docs)

    # 追加 chunk_index（全局连续编号）
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    logger.info("切分完成: %d 文档 → %d chunks", len(docs), len(chunks))
    return chunks
