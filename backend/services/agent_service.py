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

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> bytes:
    """把一个事件序列化为 SSE 数据帧：data: <json>\n\n"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


async def stream_agent_response(
    conversation_id: int,
    context: AgentContext,
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
    runtime = AgentRuntime()
    full_content: list[str] = []
    tool_results_data: list[dict] = []

    try:
        async for event in runtime.run(context, tool_names):
            if event["type"] == "text":
                full_content.append(event["content"])
            elif event["type"] == "tool_result":
                tool_results_data.append({
                    "tool": event.get("tool"),
                    "status": event.get("status"),
                    "result": event.get("result"),
                })
            yield _sse(event)
    except Exception as e:
        logger.exception("Agent 执行异常")
        yield _sse({"type": "error", "message": f"Agent 执行失败: {e}"})
        return

    # 流结束，保存完整 AI 消息（含工具结果）并更新会话时间
    async with AsyncSessionLocal() as sdb:
        assistant_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="".join(full_content),
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
        message_id = assistant_message.id

    yield _sse({
        "type": "done",
        "message_id": message_id,
        "conversation_id": conversation_id,
        "tool_results": tool_results_data if tool_results_data else None,
    })
