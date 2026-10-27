# api/agent.py
"""
Agent API —— POST /agent/{conversation_id}/messages
===========================================================================
Agent 消息入口（V0.2 设计文档 §13 新增接口）。

与普通 Chat 的 POST /conversations/{id}/messages 区分开，
保持 Chat 与 Agent 的后端业务边界清晰。

请求体（schemas/agent.py）：
    { content: str, file_ids?: int[], tools?: str[] }

响应：
    SSE 流，事件类型见 agent/runtime.py 模块文档。
===========================================================================
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.prompts import SYSTEM_PROMPT
from agent.runtime import AgentContext
from core.security import get_current_user
from db.session import get_db
from models.conversation import Conversation, ConversationType
from models.message import Message, MessageRole
from models.user import User
from schemas.agent import AgentMessageCreate
from services.agent_service import stream_agent_response
from services.knowledge_service import get_knowledge_base
from services.file_service import associate_files_with_message
from datetime import datetime

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


@router.post("/{conversation_id}/messages")
async def create_agent_message(
    conversation_id: int,
    message_data: AgentMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    向 Agent 会话发送消息，以 SSE 流式返回 Agent 执行过程。

    流程：
    1. 验证会话属于当前用户且类型为 agent
    2. 查询历史消息
    3. 保存用户消息 + 关联文件
    4. 构造 AgentContext（system prompt + 历史 + 用户消息）
    5. 流式返回 Agent 执行事件（SSE）
    """
    # 1. 验证会话归属 + 类型
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    if conversation.type != ConversationType.AGENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该会话不是 Agent 类型，请使用普通消息接口",
        )

    # 2. 查询历史消息
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    history_messages = result.scalars().all()

    # 2.1 解析生效的知识库绑定（会话级持久化）：
    #     - 请求显式携带 kb_id（数字）：校验归属后绑定并写入会话
    #     - 请求显式携带 kb_id=null：解除会话绑定
    #     - 请求未携带 kb_id：沿用会话已持久化的绑定（知识库被删则视为未绑定并自愈清理）
    kb_id: int = 0
    if "kb_id" in message_data.model_fields_set:
        if message_data.kb_id is None:
            # 显式解绑
            conversation.knowledge_base_id = None
        else:
            kb = await get_knowledge_base(db, message_data.kb_id, current_user.id)
            if kb is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="知识库不存在",
                )
            kb_id = kb.id
            # 绑定持久化到会话（与下方用户消息同一事务提交）
            conversation.knowledge_base_id = kb.id
    elif conversation.knowledge_base_id is not None:
        # 未显式指定：沿用会话绑定；KB 已被删除则清理绑定（自愈）
        kb = await get_knowledge_base(db, conversation.knowledge_base_id, current_user.id)
        if kb is not None:
            kb_id = kb.id
        else:
            conversation.knowledge_base_id = None

    # 3. 保存用户消息
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=message_data.content,
    )
    db.add(user_message)
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user_message)

    # 3.1 关联文件（如果消息携带了 file_ids）
    attached_files = []
    if message_data.file_ids:
        attached_files = await associate_files_with_message(
            file_ids=message_data.file_ids,
            message_id=user_message.id,
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db,
        )

    # 4. 构造 AgentContext（携带会话身份，供工具执行时服务端注入）
    context = AgentContext(
        system_prompt=SYSTEM_PROMPT,
        user_id=current_user.id,
        kb_id=kb_id,
    )

    # 添加对话历史（不含当前用户消息，当前消息单独添加）
    for msg in history_messages:
        context.messages.append({
            "role": msg.role.value,
            "content": msg.content,
        })

    # 4.1 注入文件元数据：让 LLM 知道本次消息携带了哪些文件
    #     （文件内容由后续工具 analyze_excel 等按需读取，不直接灌入上下文）
    if attached_files:
        file_meta_lines = [
            f"本次消息附带以下文件（使用对应工具读取内容）：",
        ]
        for f in attached_files:
            file_meta_lines.append(
                f"- file_id={f.id}，文件名={f.original_filename}，"
                f"类型={f.file_type}，大小={f.file_size} 字节"
            )
        context.messages.append({
            "role": "system",
            "content": "\n".join(file_meta_lines),
        })

    # 添加当前用户消息
    context.add_user_message(message_data.content)

    # 5. 流式返回 Agent 执行事件
    return StreamingResponse(
        stream_agent_response(
            conversation_id=conversation_id,
            context=context,
            tool_names=message_data.tools,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
