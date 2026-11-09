import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db, AsyncSessionLocal
from models.conversation import Conversation, ConversationType
from models.message import Message, MessageRole
from models.file import File
from models.user import User
from schemas.common import ApiResponse
from schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    PageResponse,
    MessageCreate,
    MessageResponse,
)
from services.llm_service import chat_with_llm_stream
from services.file_service import associate_files_with_message
from services.generation_manager import (
    GenerationHandle,
    create_generation,
    get_generation_cancel_reason,
    is_generation_cancelled,
    is_generation_finished,
    mark_generation_finished,
    remove_generation,
    request_generation_cancel,
)
from core.security import get_current_user
from datetime import datetime
from api.sse import GenerationStreamingResponse

logger = logging.getLogger(__name__)

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
# 改为分页设计，适配前端无限加载
"""
page,
page_size
"""
@router.get(
    "/recent",
    response_model=ApiResponse[PageResponse[ConversationResponse]],
)
async def get_recent_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    # limit: int = 10,
    page:int = Query(default=1, ge=1),
    page_size:int = Query(default=5, ge=1, le=100),
    # 会话类型过滤（chat / agent / knowledge），None 表示全部类型
    type: ConversationType | None = Query(default=None)
):
    """
    获取当前用户最近使用的会话，支持分页。
    page:当前页码，从1开始。
    page_size:每页条数。
    total:当前用户的会话总数。
    type:会话类型过滤（chat / agent / knowledge），不传则返回全部。
    工作台"最近使用"列表使用。
    """
    # 公共过滤条件：归属当前用户 + 可选类型过滤
    conditions = [Conversation.user_id == current_user.id]
    if type is not None:
        conditions.append(Conversation.type == type)

    #1.查询当前用户的会话总数（含类型过滤，保证分页 total 一致）
    result = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(*conditions)
    )
    total = result.scalar_one()

    # 2.根据页码计算数据库偏移量
    offset = (page - 1) * page_size
    # 3.查询当前的会话（按类型过滤）
    offResult = await db.execute(
        select(Conversation)
        .where(*conditions)
        .order_by(
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    conversations = offResult.scalars().all()

    #4.组装分页响应
    page_data = PageResponse(
        items=[
            ConversationResponse.model_validate(conv)
            for conv in conversations
        ],
        total=total,
        page=page,
        page_size=page_size
    )
    return ApiResponse(
        code=0,
        data=page_data,
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

    # 查询消息关联的文件，按 message_id 分组（含文件名/大小，供前端附件展示）
    message_ids = [m.id for m in messages]
    files_by_message: dict[int, list[dict]] = {}
    if message_ids:
        file_result = await db.execute(
            select(File).where(File.message_id.in_(message_ids))
        )
        for f in file_result.scalars().all():
            files_by_message.setdefault(f.message_id, []).append({
                "id": f.id,
                "name": f.original_filename,
                "size": f.file_size,
            })

    return ApiResponse(
        code=0,
        data=[
            MessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                files=files_by_message.get(message.id, []),
            )
            for message in messages
        ],
        message="获取消息成功"
    )

# 发送消息（SSE 流式输出）
def _sse(payload: dict) -> bytes:
    """把一个事件序列化为 SSE 数据帧：data: <json>\n\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


async def _persist_assistant_message(
    conversation_id: int,
    content: str,
    tool_results: list[dict] | None = None,
) -> int:
    """保存助手消息并返回数据库生成的消息 ID。"""
    async with AsyncSessionLocal() as sdb:
        assistant_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tool_results=tool_results,
        )
        sdb.add(assistant_message)
        await sdb.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )
        await sdb.commit()
        await sdb.refresh(assistant_message)
        return assistant_message.id


async def _stream_assistant_message(
    conversation_id: int,
    llm_messages: list[dict],
    generation: GenerationHandle,
):
    """
    流式产出 AI 回复（SSE）：
    - 逐 token 推送 delta 事件
    - 流结束后把完整 AI 回复存库，推送 done 事件（含 message_id）
    - LLM 异常时推送 error 事件

    使用独立的 DB 会话，避免与请求级 Depends(get_db) 生命周期冲突。

    断连处理说明：
    - 客户端正常收到 done/cancelled/error 后，生成会标记为 finished；
    - 客户端提前断开时，GenerationStreamingResponse 会调用本生成器的
      aclose()，代码进入最外层 finally；
    - finally 中会关闭上游 LLM 流，并用 shield 保护一次数据库写入，
      把断连前已经生成的部分回答保存下来，避免内容丢失。
    """
    full_content: list[str] = []
    message_id: int | None = None
    llm_stream = None

    try:
        # 首帧返回生成 ID，前端后续调用取消接口时使用。
        yield _sse({
            "type": "start",
            "generation_id": generation.generation_id,
            "conversation_id": conversation_id,
        })

        cancelled = False
        if is_generation_cancelled(generation):
            cancelled = True
        else:
            llm_stream = chat_with_llm_stream(llm_messages)

        try:
            if llm_stream is not None:
                async for delta in llm_stream:
                    # 协作式取消：在一个 token 边界检查停止信号。用户停止
                    # 和客户端断连都会设置同一个 cancel_event。
                    if is_generation_cancelled(generation):
                        cancelled = True
                        break
                    if not delta:
                        continue
                    full_content.append(delta)
                    yield _sse({"type": "delta", "content": delta})
        except Exception:
            logger.exception(
                "普通对话 LLM 调用失败 generation_id=%s",
                generation.generation_id,
            )
            content = "".join(full_content)
            if content:
                # 如果模型已经输出一部分后上游才失败，保留部分内容，
                # 并在消息元数据中标记中断原因，便于前端历史记录区分。
                try:
                    message_id = await _persist_assistant_message(
                        conversation_id,
                        content,
                        tool_results=[{
                            "type": "generation_cancelled",
                            "reason": "llm_error",
                        }],
                    )
                except Exception:
                    # 保存失败不能覆盖上游错误的响应逻辑；继续发送 error
                    # 帧，让前端明确结束本次生成。
                    logger.exception(
                        "保存 LLM 中断部分回答失败 generation_id=%s",
                        generation.generation_id,
                    )
            mark_generation_finished(generation)
            yield _sse({"type": "error", "message": "AI 服务调用失败"})
            return
        finally:
            # 显式关闭上游 LLM 流，及时释放网络连接。
            if llm_stream is not None:
                try:
                    await llm_stream.aclose()
                except Exception:
                    logger.exception(
                        "关闭普通对话 LLM 流失败 generation_id=%s",
                        generation.generation_id,
                    )

        content = "".join(full_content)
        if cancelled:
            # 用户主动停止和客户端断连都可能走到这里。断连通常不会继续
            # 向前端 yield，但持久化仍会在 finally 中完成。
            reason = get_generation_cancel_reason(generation) or "user"
            if content:
                try:
                    message_id = await _persist_assistant_message(
                        conversation_id,
                        content,
                        tool_results=[{
                            "type": "generation_cancelled",
                            "reason": reason,
                        }],
                    )
                except Exception:
                    logger.exception(
                        "保存取消前部分回答失败 generation_id=%s",
                        generation.generation_id,
                    )
            mark_generation_finished(generation)
            yield _sse({
                "type": "cancelled",
                "generation_id": generation.generation_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
            })
            return

        # 正常结束后保存完整回答。
        try:
            message_id = await _persist_assistant_message(
                conversation_id,
                content,
            )
        except Exception:
            logger.exception(
                "保存普通对话回答失败 generation_id=%s",
                generation.generation_id,
            )
            mark_generation_finished(generation)
            yield _sse({"type": "error", "message": "回答保存失败，请稍后重试"})
            return

        mark_generation_finished(generation)
        yield _sse({
            "type": "done",
            "generation_id": generation.generation_id,
            "message_id": message_id,
            "conversation_id": conversation_id,
        })
    finally:
        # finished=False 表示响应没有走到正常终止路径，通常就是客户端
        # 在 SSE 传输过程中断开。此时先补记原因，再尽量保存部分内容。
        if not is_generation_finished(generation):
            reason = get_generation_cancel_reason(generation)
            if reason is None:
                request_generation_cancel(
                    generation,
                    reason="client_disconnect",
                )
                reason = "client_disconnect"

            content = "".join(full_content)
            if content and message_id is None:
                try:
                    # shield 保证断连响应任务取消时，数据库事务仍有机会
                    # 完成提交；这里不再向外 yield 任何 SSE 帧。
                    await asyncio.shield(
                        _persist_assistant_message(
                            conversation_id,
                            content,
                            tool_results=[{
                                "type": "generation_cancelled",
                                "reason": reason,
                            }],
                        )
                    )
                except Exception:
                    logger.exception(
                        "保存断连部分回答失败 generation_id=%s",
                        generation.generation_id,
                    )

        # 无论正常完成、异常、取消还是断连，都要移除活动生成句柄。
        remove_generation(generation)


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

    # 4.1 关联文件（如果消息携带了 file_ids）
    # 逐个校验文件归属当前用户，然后回写 message_id 和 conversation_id
    if message_data.file_ids:
        await associate_files_with_message(
            file_ids=message_data.file_ids,
            message_id=user_message.id,
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db,
        )

    generation = create_generation(current_user.id, conversation_id)

    # 5.流式返回 AI 回复
    return GenerationStreamingResponse(
        _stream_assistant_message(conversation_id, llm_messages, generation),
        generation=generation,
    )
