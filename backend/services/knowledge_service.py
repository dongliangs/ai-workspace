"""
知识库业务服务 —— 知识库 CRUD + 权限校验。
===========================================================================
职责：
    - 创建/查询/修改/删除知识库
    - 所有操作校验 user_id 归属
    - 删除时级联清理文档 + 向量

不做的事：
    - 不处理文件上传（由 document_service 负责）
    - 不做向量检索（由 retrieval 负责）
===========================================================================
"""
import logging

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from models.document import KnowledgeDocument
from knowledge.vector_store import delete_by_knowledge_base

logger = logging.getLogger(__name__)


async def create_knowledge_base(
    db: AsyncSession,
    user_id: int,
    name: str,
    description: str | None = None,
) -> KnowledgeBase:
    """创建知识库。"""
    kb = KnowledgeBase(
        user_id=user_id,
        name=name,
        description=description,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


async def get_knowledge_bases_paginated(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[KnowledgeBase], int]:
    """分页查询当前用户的知识库列表。"""
    # 总数
    count_result = await db.execute(
        select(func.count())
        .select_from(KnowledgeBase)
        .where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE,
        )
    )
    total = count_result.scalar_one()

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE,
        )
        .order_by(KnowledgeBase.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    return list(items), total


async def get_knowledge_base(
    db: AsyncSession,
    kb_id: int,
    user_id: int,
) -> KnowledgeBase | None:
    """获取知识库详情（校验归属）。"""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_knowledge_base(
    db: AsyncSession,
    kb_id: int,
    user_id: int,
    name: str | None = None,
    description: str | None = None,
) -> KnowledgeBase | None:
    """修改知识库信息。"""
    kb = await get_knowledge_base(db, kb_id, user_id)
    if kb is None:
        return None

    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description

    await db.commit()
    await db.refresh(kb)
    return kb


async def delete_knowledge_base(
    db: AsyncSession,
    kb_id: int,
    user_id: int,
) -> bool:
    """
    删除知识库（级联清理）。

    流程：
        1. 标记状态为 deleting
        2. 删除 Milvus 中该知识库的所有向量
        3. 删除关联文档记录
        4. 删除知识库记录本身
    """
    kb = await get_knowledge_base(db, kb_id, user_id)
    if kb is None:
        return False

    # 1. 标记删除中
    kb.status = KnowledgeBaseStatus.DELETING
    await db.commit()

    # 2. 删除向量（在 try 中执行，失败不阻塞数据库删除）
    try:
        delete_by_knowledge_base(kb_id)
    except Exception as e:
        logger.error("删除知识库向量失败 kb_id=%d: %s", kb_id, e)

    # 3. 删除关联文档记录
    await db.execute(
        KnowledgeDocument.__table__.delete()
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
    )

    # 4. 删除知识库
    await db.delete(kb)
    await db.commit()
    return True


async def count_documents(
    db: AsyncSession,
    kb_id: int,
) -> int:
    """统计知识库下的文档数量。"""
    result = await db.execute(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == kb_id)
    )
    return result.scalar_one()
