import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db, AsyncSessionLocal
from models.conversation import Conversation
from models.message import Message, MessageRole
from models.user import User
from schemas.common import ApiResponse
from schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from services.llm_service import chat_with_llm_stream
from core.security import get_current_user
from datetime import datetime

router = APIRouter(
    prefix="/conversations",
    tags=["conversation"],
)

@router.post(
    "/create",
    response_model=ApiResponse[ConversationResponse],
)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建一个新的 Chat 会话。
    工作台输入框发送后调用，得到 conversation_id 后跳转 /chat/:id。
    """
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title,
        type=data.type,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ApiResponse(
        code=0,
        data=ConversationResponse.model_validate(conversation),
        message="创建会话成功",
    )

# 获取当前用户最近使用的会话
@router.get(
    "/recent",
    response_model=ApiResponse[list[ConversationResponse]],
)
async def get_recent_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
):
    """
    获取当前用户最近使用的会话，按 updated_at 倒序。
    工作台"最近使用"列表使用。
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    return ApiResponse(
        code=0,
        data=[
            ConversationResponse.model_validate(conv)
            for conv in conversations
        ],
        message="获取最近会话成功",
    )

#查询会话  ，获取某个会话的基本信息

@router.get(
    "/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
)
async def get_conversation(
        conversation_id: int,
        content_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == content_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在"
        )

    return ApiResponse(
        code=0,
        data=ConversationResponse.model_validate(conversation),
        message="获取会话成功"
    )

# 查询历史消息
@router.get(
    "/{conversation_id}/messages",
    response_model=ApiResponse[list[MessageResponse]]
)
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 先确认这个会话属于当前用户
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )

    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在"
        )

    # 查询消息
    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id
        )
        .order_by(Message.created_at.asc())
    )

    messages = result.scalars().all()

    return ApiResponse(
        code=0,
        data=[
            MessageResponse.model_validate(message)
            for message in messages
        ],
        message="获取消息成功"
    )

# 发送消息（SSE 流式输出）
def _sse(payload: dict) -> bytes:
    """把一个事件序列化为 SSE 数据帧：data: <json>\n\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


async def _stream_assistant_message(conversation_id: int, llm_messages: list[dict]):
    """
    流式产出 AI 回复（SSE）：
    - 逐 token 推送 delta 事件
    - 流结束后把完整 AI 回复存库，推送 done 事件（含 message_id）
    - LLM 异常时推送 error 事件

    使用独立的 DB 会话，避免与请求级 Depends(get_db) 生命周期冲突。
    """
    full_content: list[str] = []
    try:
        async for delta in chat_with_llm_stream(llm_messages):
            if not delta:
                continue
            full_content.append(delta)
            yield _sse({"type": "delta", "content": delta})
    except Exception:
        yield _sse({"type": "error", "message": "AI 服务调用失败"})
        return

    # 流结束，保存完整 AI 消息并更新会话时间
    async with AsyncSessionLocal() as sdb:
        assistant_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="".join(full_content),
        )
        sdb.add(assistant_message)
        await sdb.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )
        await sdb.commit()
        await sdb.refresh(assistant_message)
        message_id = assistant_message.id

    yield _sse({
        "type": "done",
        "message_id": message_id,
        "conversation_id": conversation_id,
    })


@router.post(
    "/{conversation_id}/messages",
)
async def create_message(
    conversation_id:int,
    message_data:MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    向指定会话发送消息，以 SSE 流式返回 AI 回复。
    流程：
    1.验证conversation是否属于当前用户
    2.查询历史消息
    3.保存用户消息、更新会话时间
    4.流式调用LLM（SSE）
    5.流结束后保存完整AI消息
    """
    result= await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    # 2.查询历史消息
    result= await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id
        )
        .order_by(Message.created_at.asc())
    )

    history_message = result.scalars().all()

    # 3. 组装发送给LLM 的消息

    llm_messages = []

    for message in history_message:
        llm_messages.append({
            "role": message.role.value,
            "content": message.content,
        })

    # 当前用户消息
    llm_messages.append({
        "role": "user",
        "content": message_data.content,
    })

    # 4.保存用户消息（在开始流式响应前持久化）
    user_message = Message(
        conversation_id = conversation_id,
        role=MessageRole.USER,
        content=message_data.content
    )

    db.add(user_message)
    conversation.updated_at = datetime.utcnow()
    await db.commit()

    # 5.流式返回 AI 回复
    return StreamingResponse(
        _stream_assistant_message(conversation_id, llm_messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭代理缓冲，保证实时推送
        },
    )
