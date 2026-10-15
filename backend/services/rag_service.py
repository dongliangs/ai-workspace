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
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal
from models.conversation import Conversation
from models.message import Message, MessageRole
from models.document import KnowledgeDocument
from knowledge.retrieval import retrieve
from knowledge.prompts import RAG_SYSTEM_PROMPT, build_rag_context
from services.llm_service import chat_with_llm_stream

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


async def rag_chat_stream(
    question: str,
    user_id: int,
    kb_id: int,
    conversation_id: int,
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
    # ── 1. 检索 ──────────────────────────────
    yield _sse({"type": "start"})
    yield _sse({"type": "retrieval_start", "kb_id": kb_id})

    try:
        chunks = retrieve(question, user_id, kb_id)
    except Exception as e:
        logger.error("检索失败: %s", e)
        yield _sse({"type": "error", "message": "知识库检索失败"})
        return

    if not chunks:
        yield _sse({
            "type": "retrieval_result",
            "sources": [],
            "message": "未找到相关资料",
        })

        full_content = "当前知识库中没有找到与您问题相关的资料。请尝试上传更多文档或调整问题后重试。"
        yield _sse({"type": "text", "content": full_content})

        async with AsyncSessionLocal() as db:
            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=full_content,
                tool_results=[{"type": "rag_no_results", "kb_id": kb_id}],
            )
            db.add(assistant_msg)
            await db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(updated_at=datetime.utcnow())
            )
            await db.commit()
            await db.refresh(assistant_msg)

        yield _sse({
            "type": "done",
            "message_id": assistant_msg.id,
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
    full_content_parts: list[str] = []

    try:
        async for delta in chat_with_llm_stream(llm_messages):
            if not delta:
                continue
            full_content_parts.append(delta)
            yield _sse({"type": "text", "content": delta})
    except Exception:
        yield _sse({"type": "error", "message": "AI 服务调用失败"})
        return

    # ── 5. 持久化 ───────────────────────────
    full_content = "".join(full_content_parts)
    source_refs = [
        {
            "index": s["index"],
            "document_id": s["document_id"],
            "filename": s["filename"],
            "page_number": s["page_number"],
        }
        for s in sources
    ]

    async with AsyncSessionLocal() as db:
        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=full_content,
            tool_results=[{
                "type": "rag_sources",
                "sources": source_refs,
            }],
        )
        db.add(assistant_msg)
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.utcnow())
        )
        await db.commit()
        await db.refresh(assistant_msg)

    yield _sse({
        "type": "done",
        "message_id": assistant_msg.id,
        "conversation_id": conversation_id,
        "sources": source_refs,
    })
