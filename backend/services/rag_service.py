"""
RAG 服务 —— 检索增强生成的业务协调层。
===========================================================================
职责：
    1. 调用 LangChain Retriever 检索相关片段
    2. 组装上下文 + 来源元数据
    3. 调用 DeepSeek 生成答案
    4. 通过 SSE 推送检索状态、文本增量、来源和结束事件
    5. 持久化用户问题和助手回答

不做的事：
    - 不直接操作向量库（通过 retrieval 间接调用）
    - 不做 Agent 工具调用（Agent 通过 knowledge_search 工具间接复用）
===========================================================================
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal
from core.async_execution import run_retrieval_sync
from models.conversation import Conversation
from models.message import Message, MessageRole
from models.document import KnowledgeDocument
from knowledge.retrieval import retrieve
from knowledge.prompts import RAG_SYSTEM_PROMPT, build_rag_context
from services.llm_service import chat_with_llm_stream
from services.generation_manager import (
    GenerationHandle,
    get_generation_cancel_reason,
    is_generation_cancelled,
    is_generation_finished,
    mark_generation_finished,
    remove_generation,
    request_generation_cancel,
)

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> bytes:
    """把一个事件序列化为 SSE 数据帧。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


async def _get_document_names(db: AsyncSession, doc_ids: list[int]) -> dict[int, str]:
    """批量查文档名，返回 document_id → filename 映射。"""
    if not doc_ids:
        return {}
    result = await db.execute(
        select(KnowledgeDocument.id, KnowledgeDocument.filename)
        .where(KnowledgeDocument.id.in_(doc_ids))
    )
    return {row.id: row.filename for row in result.all()}


async def _persist_assistant_message(
    conversation_id: int,
    content: str,
    tool_results: list[dict],
) -> int:
    """保存 RAG 助手回答及其来源信息，并返回消息 ID。"""
    async with AsyncSessionLocal() as db:
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tool_results=tool_results,
        )
        db.add(assistant_msg)
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )
        await db.commit()
        await db.refresh(assistant_msg)
        return assistant_msg.id


async def rag_chat_stream(
    question: str,
    user_id: int,
    kb_id: int,
    conversation_id: int,
    generation: GenerationHandle,
) -> AsyncGenerator[bytes, None]:
    """
    知识库问答 SSE 流式生成。

    事件序列:
        start              → 开始
        retrieval_start    → 正在检索
        retrieval_result    → 检索到的来源元数据
        text                → LLM 回答增量（多次）
        done                → 结束（含 message_id）
        error               → 异常

    内部使用 LangChain Embeddings + VectorStore Retriever 检索。
    """
    full_content_parts: list[str] = []
    source_refs: list[dict] = []
    message_id: int | None = None
    llm_stream = None

    try:
        # ── 1. 检索 ──────────────────────────────
        yield _sse({
            "type": "start",
            "generation_id": generation.generation_id,
            "conversation_id": conversation_id,
        })
        yield _sse({"type": "retrieval_start", "kb_id": kb_id})

        if is_generation_cancelled(generation):
            mark_generation_finished(generation)
            yield _sse({
                "type": "cancelled",
                "generation_id": generation.generation_id,
                "conversation_id": conversation_id,
                "message_id": None,
            })
            return

        try:
            # retrieve 内部包含同步的 Embedding 推理和 Milvus 查询，
            # 必须通过检索线程池执行，避免卡住当前 SSE 事件循环。
            chunks = await run_retrieval_sync(
                retrieve,
                question,
                user_id,
                kb_id,
                operation=f"retrieve(kb_id={kb_id})",
            )
        except Exception:
            logger.exception("检索失败 kb_id=%d", kb_id)
            mark_generation_finished(generation)
            yield _sse({"type": "error", "message": "知识库检索失败"})
            return

        # 检索线程无法被中途强制终止，返回后先检查用户是否已经停止。
        if is_generation_cancelled(generation):
            mark_generation_finished(generation)
            yield _sse({
                "type": "cancelled",
                "generation_id": generation.generation_id,
                "conversation_id": conversation_id,
                "message_id": None,
            })
            return

        if not chunks:
            yield _sse({
                "type": "retrieval_result",
                "sources": [],
                "message": "未找到相关资料",
            })

            full_content = "当前知识库中没有找到与您问题相关的资料。请尝试上传更多文档或调整问题后重试。"
            yield _sse({"type": "text", "content": full_content})
            try:
                message_id = await _persist_assistant_message(
                    conversation_id,
                    full_content,
                    tool_results=[{"type": "rag_no_results", "kb_id": kb_id}],
                )
            except Exception:
                logger.exception(
                    "保存无检索结果回答失败 generation_id=%s",
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
            return

        # ── 2. 组装上下文 ────────────────────────
        async with AsyncSessionLocal() as db:
            doc_ids = list({c["document_id"] for c in chunks})
            doc_names = await _get_document_names(db, doc_ids)

        context_text = build_rag_context(chunks, doc_names)

        # 推送来源元数据给前端
        sources = []
        for i, chunk in enumerate(chunks, 1):
            sources.append({
                "index": i,
                "document_id": chunk["document_id"],
                "filename": doc_names.get(chunk["document_id"], "未知"),
                "page_number": chunk.get("page_number", -1),
                "chunk_index": chunk.get("chunk_index", 0),
                "score": round(chunk.get("score", 0.0), 4),
            })

        yield _sse({"type": "retrieval_result", "sources": sources})

        source_refs = [
            {
                "index": s["index"],
                "document_id": s["document_id"],
                "filename": s["filename"],
                "page_number": s["page_number"],
            }
            for s in sources
        ]

        # ── 3. 组装 LLM 消息 ──────────────────────
        user_content = (
            f"检索资料：\n{context_text}\n\n"
            f"---\n\n用户问题：{question}"
        )

        llm_messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # ── 4. 流式生成回答 ──────────────────────
        cancelled = False

        if is_generation_cancelled(generation):
            cancelled = True
        else:
            llm_stream = chat_with_llm_stream(llm_messages)

        try:
            if llm_stream is not None:
                async for delta in llm_stream:
                    # 协作式取消：在每个 token 边界检查停止信号。
                    if is_generation_cancelled(generation):
                        cancelled = True
                        break
                    if not delta:
                        continue
                    full_content_parts.append(delta)
                    yield _sse({"type": "text", "content": delta})
        except Exception:
            logger.exception(
                "RAG LLM 调用失败 generation_id=%s",
                generation.generation_id,
            )
            full_content = "".join(full_content_parts)
            if full_content:
                # 模型已经输出部分内容时先保存，再返回错误，避免整段内容
                # 因一次网络抖动在历史记录中完全丢失。
                persisted_results = [
                    {"type": "rag_sources", "sources": source_refs},
                    {"type": "generation_cancelled", "reason": "llm_error"},
                ]
                try:
                    message_id = await _persist_assistant_message(
                        conversation_id,
                        full_content,
                        tool_results=persisted_results,
                    )
                except Exception:
                    logger.exception(
                        "保存 RAG LLM 中断部分回答失败 generation_id=%s",
                        generation.generation_id,
                    )
            mark_generation_finished(generation)
            yield _sse({"type": "error", "message": "AI 服务调用失败"})
            return
        finally:
            # 释放上游 LLM 流，避免停止后继续占用网络连接。
            if llm_stream is not None:
                try:
                    await llm_stream.aclose()
                except Exception:
                    logger.exception(
                        "关闭 RAG LLM 流失败 generation_id=%s",
                        generation.generation_id,
                    )

        full_content = "".join(full_content_parts)
        if cancelled:
            reason = get_generation_cancel_reason(generation) or "user"
            if full_content:
                try:
                    message_id = await _persist_assistant_message(
                        conversation_id,
                        full_content,
                        tool_results=[
                            {"type": "rag_sources", "sources": source_refs},
                            {"type": "generation_cancelled", "reason": reason},
                        ],
                    )
                except Exception:
                    logger.exception(
                        "保存 RAG 取消前部分回答失败 generation_id=%s",
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

        try:
            message_id = await _persist_assistant_message(
                conversation_id,
                full_content,
                tool_results=[{
                    "type": "rag_sources",
                    "sources": source_refs,
                }],
            )
        except Exception:
            logger.exception(
                "保存 RAG 回答失败 generation_id=%s",
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
            "sources": source_refs,
        })
    finally:
        # 客户端断连时，响应层会主动关闭当前异步生成器。只要生成器没有
        # 走到正常终止路径，就在这里保存已经输出的部分回答并清理任务。
        if not is_generation_finished(generation):
            reason = get_generation_cancel_reason(generation)
            if reason is None:
                request_generation_cancel(
                    generation,
                    reason="client_disconnect",
                )
                reason = "client_disconnect"

            full_content = "".join(full_content_parts)
            if full_content and message_id is None:
                persisted_results = [
                    {"type": "rag_sources", "sources": source_refs},
                    {"type": "generation_cancelled", "reason": reason},
                ]
                try:
                    await asyncio.shield(
                        _persist_assistant_message(
                            conversation_id,
                            full_content,
                            tool_results=persisted_results,
                        )
                    )
                except Exception:
                    logger.exception(
                        "保存断连 RAG 部分回答失败 generation_id=%s",
                        generation.generation_id,
                    )

        # 任何退出路径都要清理活动生成注册信息。
        remove_generation(generation)
