# services/agent_service.py
"""
Agent Service —— Agent 执行编排层。
===========================================================================
职责（V0.2 设计文档 §5 + §13）：
    1. 验证会话属于当前用户且类型为 agent
    2. 查询历史消息
    3. 保存用户消息 + 关联文件
    4. 构造 AgentContext（system prompt + 历史 + 用户消息）
    5. 运行 AgentRuntime，流式推送 SSE 事件
    6. 流结束后保存完整 Assistant Message
    7. 推送 done 事件（含 message_id）

与 conversation.py 中普通 Chat 流程的区别：
    - Chat  直接调 LLM 流式输出文本
    - Agent 通过 Agent Loop 循环调用 LLM + Tools，推送多类型事件
===========================================================================
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent.prompts import SYSTEM_PROMPT
from agent.runtime import AgentContext, AgentRuntime
from db.session import AsyncSessionLocal
from models.conversation import Conversation
from models.message import Message, MessageRole
from services.file_service import associate_files_with_message
from services.generation_manager import (
    GenerationHandle,
    get_generation_cancel_reason,
    is_generation_finished,
    mark_generation_finished,
    remove_generation,
    request_generation_cancel,
)

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> bytes:
    """把一个事件序列化为 SSE 数据帧：data: <json>\n\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


async def stream_agent_response(
    conversation_id: int,
    context: AgentContext,
    generation: GenerationHandle,
    tool_names: list[str] | None = None,
) -> AsyncGenerator[bytes, None]:
    """
    运行 Agent Runtime，流式产出 SSE 事件帧。

    流程：
    1. 通过 AgentRuntime 执行 Agent Loop，逐个 yield 事件
    2. 收集所有 text 事件内容
    3. 流结束后保存完整 Assistant Message 到数据库
    4. 推送 done 事件（含 message_id）

    使用独立的 DB 会话保存消息，避免与请求级 Depends(get_db) 生命周期冲突。
    """
    full_content: list[str] = []
    tool_results_data: list[dict] = []
    message_id: int | None = None

    try:
        runtime = AgentRuntime()
        cancelled = False

        try:
            async for event in runtime.run(
                context,
                tool_names,
                generation.cancel_event,
            ):
                if event["type"] == "generation_cancelled":
                    # 取消事件由 service 统一持久化后再发送，避免重复通知。
                    cancelled = True
                    break

                if event["type"] == "agent_start":
                    event = {
                        **event,
                        "generation_id": generation.generation_id,
                        "conversation_id": conversation_id,
                    }

                if event["type"] == "text":
                    full_content.append(event["content"])
                elif event["type"] == "tool_result":
                    tool_results_data.append({
                        "tool": event.get("tool"),
                        "status": event.get("status"),
                        "result": event.get("result"),
                    })
                elif event["type"] == "error":
                    # AgentRuntime 在 LLM 超时、重试耗尽或熔断时返回 error。
                    # 如果此前已经输出过文本或执行过工具，先保留部分结果，
                    # 再把错误帧发给前端，避免历史记录里出现一条“成功”消息。
                    content = "".join(full_content)
                    if content or tool_results_data:
                        persisted_results = list(tool_results_data)
                        persisted_results.append({
                            "type": "generation_cancelled",
                            "reason": "llm_error",
                        })
                        try:
                            message_id = await _persist_agent_message(
                                conversation_id,
                                content,
                                persisted_results,
                            )
                        except Exception:
                            logger.exception(
                                "保存 Agent LLM 中断结果失败 generation_id=%s",
                                generation.generation_id,
                            )
                    mark_generation_finished(generation)
                    yield _sse({
                        **event,
                        "generation_id": generation.generation_id,
                        "conversation_id": conversation_id,
                    })
                    return

                yield _sse(event)
        except Exception:
            logger.exception("Agent 执行异常")
            content = "".join(full_content)
            if content or tool_results_data:
                persisted_results = list(tool_results_data)
                persisted_results.append({
                    "type": "generation_cancelled",
                    "reason": "agent_error",
                })
                try:
                    message_id = await _persist_agent_message(
                        conversation_id,
                        content,
                        persisted_results,
                    )
                except Exception:
                    logger.exception(
                        "保存 Agent 异常前结果失败 generation_id=%s",
                        generation.generation_id,
                    )
            mark_generation_finished(generation)
            # 不向前端暴露内部异常文本。
            yield _sse({"type": "error", "message": "Agent 执行失败"})
            return

        content = "".join(full_content)
        if cancelled:
            reason = get_generation_cancel_reason(generation) or "user"
            persisted_results = list(tool_results_data)
            persisted_results.append({
                "type": "generation_cancelled",
                "reason": reason,
            })
            if content or tool_results_data:
                try:
                    message_id = await _persist_agent_message(
                        conversation_id,
                        content,
                        persisted_results,
                    )
                except Exception:
                    logger.exception(
                        "保存 Agent 取消前结果失败 generation_id=%s",
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

        # 流正常结束，保存完整 AI 消息和工具结果。
        try:
            message_id = await _persist_agent_message(
                conversation_id,
                content,
                tool_results_data,
            )
        except Exception:
            logger.exception(
                "保存 Agent 回答失败 generation_id=%s",
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
            "tool_results": tool_results_data if tool_results_data else None,
        })
    finally:
        # 客户端在 SSE 中途断开时，响应层会 aclose 当前生成器。这里保存
        # 断连前已经产生的文本和工具结果，并确保活动任务被移除。
        if not is_generation_finished(generation):
            reason = get_generation_cancel_reason(generation)
            if reason is None:
                request_generation_cancel(
                    generation,
                    reason="client_disconnect",
                )
                reason = "client_disconnect"

            content = "".join(full_content)
            if (content or tool_results_data) and message_id is None:
                persisted_results = list(tool_results_data)
                persisted_results.append({
                    "type": "generation_cancelled",
                    "reason": reason,
                })
                try:
                    await asyncio.shield(
                        _persist_agent_message(
                            conversation_id,
                            content,
                            persisted_results,
                        )
                    )
                except Exception:
                    logger.exception(
                        "保存断连 Agent 部分结果失败 generation_id=%s",
                        generation.generation_id,
                    )

        remove_generation(generation)


async def _persist_agent_message(
    conversation_id: int,
    content: str,
    tool_results_data: list[dict],
) -> int:
    """保存 Agent 回答和工具执行结果，并返回消息 ID。"""
    async with AsyncSessionLocal() as sdb:
        assistant_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tool_results=tool_results_data if tool_results_data else None,
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
