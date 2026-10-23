"""
文档服务 —— 文件上传到知识库 + 索引构建 + 文档删除。
===========================================================================
职责：
    - 接收文件上传，复用 File Service 保存
    - 创建 KnowledgeDocument 记录
    - 触发索引构建（LangChain Loader → Splitter → VectorStore）
    - 查询/删除文档
    - 删除时同步清理向量

索引流程（LangChain 链路）：
    1. 状态置为 processing
    2. LangChain Loader 加载文档 → list[Document]
    3. LangChain Text Splitter 切分 → list[Document]（追加 chunk_index）
    4. 追加 user_id / kb_id / document_id 到 metadata
    5. LangChain VectorStore.add_documents → 自动向量化 + 写入 Milvus
    6. 状态置为 indexed，记录 chunk_count
    7. 失败则置为 failed，记录 error_message
===========================================================================
"""
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import KnowledgeDocument, DocumentStatus
from models.knowledge_base import KnowledgeBase
from models.file import File
from knowledge.loaders import load_document
from knowledge.chunker import split_documents
from knowledge.vector_store import add_documents, delete_by_document

logger = logging.getLogger(__name__)


async def create_and_index(
    db: AsyncSession,
    kb_id: int,
    user_id: int,
    file_record: File,
    filename: str,
    file_type: str,
) -> KnowledgeDocument:
    """
    创建文档记录并构建索引。

    文件已由 API 层通过 save_upload_file 保存到磁盘，
    本函数只负责创建 KnowledgeDocument + 索引构建。

    Returns:
        创建的 KnowledgeDocument（状态为 indexed 或 failed）
    """
    # 1. 创建文档记录（doc_count 在索引成功后才计入）
    doc = KnowledgeDocument(
        knowledge_base_id=kb_id,
        user_id=user_id,
        file_id=file_record.id,
        filename=filename,
        file_type=file_type,
        status=DocumentStatus.PROCESSING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 2. 构建索引；失败则置为 failed（不计入知识库文档数量）
    try:
        await _build_index(db, doc, file_record.storage_path)
    except Exception as e:
        logger.error("文档索引失败 doc_id=%d: %s", doc.id, e)
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)[:500]
        await db.commit()
        await db.refresh(doc)
        return doc

    # 3. 索引成功，重算知识库文档计数
    await _refresh_doc_count(db, kb_id)
    return doc


async def retry_index(
    db: AsyncSession,
    doc_id: int,
    user_id: int,
) -> KnowledgeDocument | None:
    """
    重试索引失败的文档。

    仅 status=failed 的文档可重试：先清理可能残留的旧向量（部分写入场景），
    再重新走完整构建链路。成功转 indexed 并重算 doc_count，
    再次失败则保持 failed 并更新 error_message。

    Returns:
        更新后的文档；doc_id 不存在或不属于该用户时返回 None
    """
    doc = await get_document(db, doc_id, user_id)
    if doc is None:
        return None
    if doc.status != DocumentStatus.FAILED:
        raise ValueError("仅索引失败的文档可以重试")

    # 1. 清理残留向量（失败前可能已部分写入）
    try:
        delete_by_document(doc_id)
    except Exception as e:
        logger.warning("重试前清理旧向量失败 doc_id=%d: %s", doc_id, e)

    # 2. 状态回到 processing，清空旧错误信息
    doc.status = DocumentStatus.PROCESSING
    doc.error_message = None
    await db.commit()
    await db.refresh(doc)

    # 3. 复用原始文件重新构建
    file_record = await db.get(File, doc.file_id)
    try:
        await _build_index(db, doc, file_record.storage_path)
    except Exception as e:
        logger.error("重试索引失败 doc_id=%d: %s", doc.id, e)
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)[:500]
        await db.commit()
        await db.refresh(doc)
        return doc

    # 4. 成功，重算知识库文档计数
    await _refresh_doc_count(db, doc.knowledge_base_id)
    return doc


async def _build_index(
    db: AsyncSession,
    doc: KnowledgeDocument,
    storage_path: str,
) -> None:
    """
    执行索引构建流程（LangChain 链路）：
    Loader → Splitter → 追加 metadata → VectorStore.add_documents

    VectorStore.add_documents 内部自动调用 Embeddings.embed_documents 向量化。
    """
    file_path = Path(storage_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {storage_path}")

    # 1. LangChain Loader 加载文档
    docs = load_document(file_path, doc.file_type)
    if not docs:
        raise ValueError("文件内容为空或无法解析")
    logger.info("文档加载完成 doc_id=%d, %d 个文档", doc.id, len(docs))

    # 2. LangChain Text Splitter 切分
    chunks = split_documents(docs)
    if not chunks:
        raise ValueError("切分结果为空")
    logger.info("文档切分完成 doc_id=%d, %d chunks", doc.id, len(chunks))

    # 3. 追加业务 metadata（供检索过滤和删除）
    for chunk in chunks:
        chunk.metadata["user_id"] = doc.user_id
        chunk.metadata["kb_id"] = doc.knowledge_base_id
        chunk.metadata["document_id"] = doc.id

    # 4. LangChain VectorStore 写入（自动向量化 + 写入 Milvus）
    written = add_documents(chunks)
    logger.info("向量写入完成 doc_id=%d, %d 条", doc.id, written)

    # 5. 更新状态
    doc.status = DocumentStatus.INDEXED
    doc.chunk_count = len(chunks)
    doc.indexed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(doc)
    logger.info("索引构建完成 doc_id=%d, chunks=%d", doc.id, len(chunks))


async def get_documents_paginated(
    db: AsyncSession,
    kb_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeDocument], int]:
    """分页查询知识库文档列表。"""
    count_result = await db.execute(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
        .order_by(KnowledgeDocument.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    return list(items), total


async def get_document(
    db: AsyncSession,
    doc_id: int,
    user_id: int,
) -> KnowledgeDocument | None:
    """获取文档详情（校验归属）。"""
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    doc_id: int,
    user_id: int,
) -> bool:
    """删除文档（同步清理向量）。"""
    doc = await get_document(db, doc_id, user_id)
    if doc is None:
        return False

    kb_id = doc.knowledge_base_id

    # 清理向量
    try:
        delete_by_document(doc_id)
    except Exception as e:
        logger.error("删除文档向量失败 doc_id=%d: %s", doc_id, e)

    # 删除文档记录，并重算知识库文档计数
    await db.delete(doc)
    await _refresh_doc_count(db, kb_id)
    return True


async def _refresh_doc_count(db: AsyncSession, kb_id: int) -> None:
    """
    按「索引成功」的文档数重算知识库 doc_count。

    只有 status=indexed 的文档计入数量（failed/processing 不计），
    且重算可自愈历史增量计数漂移。
    """
    result = await db.execute(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(
            KnowledgeDocument.knowledge_base_id == kb_id,
            KnowledgeDocument.status == DocumentStatus.INDEXED,
        )
    )
    kb = await db.get(KnowledgeBase, kb_id)
    kb.doc_count = result.scalar_one()
    await db.commit()
