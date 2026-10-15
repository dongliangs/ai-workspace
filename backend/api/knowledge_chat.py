"""
知识库问答 API 路由 —— SSE 流式问答。
===========================================================================
路径前缀: /knowledge-bases/{kb_id}/chat
流程：
    1. 校验知识库归属
    2. 创建或复用 knowledge 类型会话
    3. 保存用户问题
    4. SSE 流式推送检索结果 + LLM 回答
===========================================================================
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from db.session import get_db, AsyncSessionLocal
from models.user import User
from models.conversation import Conversation, ConversationType
from models.message import Message, MessageRole
from schemas.common import ApiResponse
from schemas.document import KnowledgeChatRequest
from services.knowledge_service import get_knowledge_base
from services.rag_service import rag_chat_stream, _sse

router = APIRouter(tags=["knowledge-chat"])


@router.post("/knowledge-bases/{kb_id}/chat")
async def knowledge_chat(
    kb_id: int,
    data: KnowledgeChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    知识库问答（SSE 流式返回）。

    事件序列:
        start → retrieval_start → retrieval_result → text(多次) → done
    """
    # 1. 校验知识库归属
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 2. 创建或复用会话
    conversation_id = data.conversation_id
    if conversation_id is None:
        # 创建新的 knowledge 类型会话
        conv = Conversation(
            user_id=current_user.id,
            title=data.question[:50],
            type=ConversationType.KNOWLEDGE,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conversation_id = conv.id
    else:
        # 校验会话归属
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            raise HTTPException(status_code=404, detail="会话不存在")

    # 3. 保存用户问题
    user_msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=data.question,
    )
    db.add(user_msg)
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=datetime.utcnow())
    )
    await db.commit()

    # 4. SSE 流式返回
    return StreamingResponse(
        rag_chat_stream(
            question=data.question,
            user_id=current_user.id,
            kb_id=kb_id,
            conversation_id=conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
