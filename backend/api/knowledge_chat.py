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
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from db.session import get_db, AsyncSessionLocal
from models.user import User
from models.message import Message, MessageRole
from schemas.common import ApiResponse
from schemas.document import KnowledgeChatRequest
from models.conversation import Conversation, ConversationType
from services.knowledge_service import (
    get_knowledge_base,
    resolve_knowledge_conversation,
)
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

    # 2. 解析会话（服务端持久化绑定：请求指定 → 复用 kb 绑定 → 新建并绑定）
    try:
        conv = await resolve_knowledge_conversation(
            db,
            kb,
            current_user.id,
            requested_conversation_id=data.conversation_id,
            default_title=data.question[:50],
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation_id = conv.id

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
