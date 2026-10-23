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
from models.conversation import Conversation, ConversationType
from models.document import KnowledgeDocument, DocumentStatus
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


async def sum_chunk_counts(
    db: AsyncSession,
    kb_ids: list[int],
) -> dict[int, int]:
    """
    批量统计各知识库的可检索片段总数（仅统计索引成功文档的分块）。

    实时聚合而非在知识库表冗余存储计数：天然与文档索引状态一致，无漂移。
    """
    if not kb_ids:
        return {}
    result = await db.execute(
        select(
            KnowledgeDocument.knowledge_base_id,
            func.sum(KnowledgeDocument.chunk_count),
        )
        .where(
            KnowledgeDocument.knowledge_base_id.in_(kb_ids),
            KnowledgeDocument.status == DocumentStatus.INDEXED,
        )
        .group_by(KnowledgeDocument.knowledge_base_id)
    )
    return {kb_id: int(total or 0) for kb_id, total in result.all()}


async def _get_valid_knowledge_conversation(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
) -> Conversation | None:
    """获取归属当前用户且类型为 knowledge 的会话（无效返回 None）。"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.type == ConversationType.KNOWLEDGE,
        )
    )
    return result.scalar_one_or_none()


async def resolve_knowledge_conversation(
    db: AsyncSession,
    kb: KnowledgeBase,
    user_id: int,
    requested_conversation_id: int | None = None,
    default_title: str = "知识库问答",
) -> Conversation:
    """
    解析知识库问答使用的会话（绑定关系服务端持久化，不依赖前端保存）。

    优先级：
        1. 请求显式携带 conversation_id：校验归属/类型后复用，并回填 kb 绑定
        2. 知识库已绑定会话且仍有效：直接复用（重进问答续接历史，不新建会话）
        3. 否则：创建新 knowledge 会话并写入 kb.conversation_id 绑定

    Raises:
        ValueError: 显式指定的会话不存在/不属于当前用户/不是 knowledge 类型
    """
    # 1. 显式指定的会话
    if requested_conversation_id is not None:
        conv = await _get_valid_knowledge_conversation(
            db, requested_conversation_id, user_id
        )
        if conv is None:
            raise ValueError("会话不存在")
        # 回填绑定（首次使用该会话、或用户切换了会话）
        if kb.conversation_id != conv.id:
            kb.conversation_id = conv.id
            await db.commit()
        return conv

    # 2. 复用已绑定会话（会话被删则绑定失效，落到新建分支）
    if kb.conversation_id is not None:
        conv = await _get_valid_knowledge_conversation(
            db, kb.conversation_id, user_id
        )
        if conv is not None:
            return conv

    # 3. 新建会话并绑定到知识库
    conv = Conversation(
        user_id=user_id,
        title=default_title,
        type=ConversationType.KNOWLEDGE,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    kb.conversation_id = conv.id
    await db.commit()
    return conv
