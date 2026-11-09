import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import api.conversation as conversation_module
import services.agent_service as agent_service_module
import services.generation_manager as generation_manager
import services.rag_service as rag_module
from agent.registry import ToolRegistry
from agent.runtime import AgentContext, AgentRuntime
from api.generation import cancel_generation_request
from services.generation_manager import (
    cancel_generation,
    create_generation,
    remove_generation,
    request_generation_cancel,
)


@pytest.fixture(autouse=True)
def clear_generation_registry():
    generation_manager._active_generations.clear()
    yield
    generation_manager._active_generations.clear()


class _FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def _sse_payloads(frames):
    return [
        json.loads(frame.decode("utf-8").removeprefix("data: ").strip())
        for frame in frames
    ]


def test_cancel_generation_checks_ownership_and_sets_signal():
    handle = create_generation(user_id=1, conversation_id=2)

    assert cancel_generation(handle.generation_id, user_id=99) is None
    assert handle.cancel_event.is_set() is False

    cancelled = cancel_generation(handle.generation_id, user_id=1)
    assert cancelled is handle
    assert handle.cancel_event.is_set() is True

    remove_generation(handle)
    assert cancel_generation(handle.generation_id, user_id=1) is None


@pytest.mark.asyncio
async def test_cancel_endpoint_rejects_other_user():
    handle = create_generation(user_id=1, conversation_id=2)

    with pytest.raises(HTTPException) as exc_info:
        await cancel_generation_request(
            handle.generation_id,
            current_user=type("User", (), {"id": 99})(),
        )

    assert exc_info.value.status_code == 404
    assert handle.cancel_event.is_set() is False


@pytest.mark.asyncio
async def test_cancel_endpoint_accepts_owner():
    handle = create_generation(user_id=1, conversation_id=2)

    response = await cancel_generation_request(
        handle.generation_id,
        current_user=type("User", (), {"id": 1})(),
    )

    assert response.data.generation_id == handle.generation_id
    assert response.data.status == "cancelling"
    assert handle.cancel_event.is_set() is True


@pytest.mark.asyncio
async def test_chat_stream_stops_and_persists_partial_content():
    handle = create_generation(user_id=1, conversation_id=2)

    async def fake_llm_stream(messages):
        yield "first"
        handle.cancel_event.set()
        yield "ignored"

    persist = AsyncMock(return_value=55)
    with patch.object(
        conversation_module,
        "chat_with_llm_stream",
        new=fake_llm_stream,
    ), patch.object(
        conversation_module,
        "_persist_assistant_message",
        new=persist,
    ):
        frames = [
            frame
            async for frame in conversation_module._stream_assistant_message(
                conversation_id=2,
                llm_messages=[],
                generation=handle,
            )
        ]

    payloads = _sse_payloads(frames)
    assert [item["type"] for item in payloads] == [
        "start",
        "delta",
        "cancelled",
    ]
    assert payloads[1]["content"] == "first"
    assert payloads[-1]["message_id"] == 55
    persist.assert_awaited_once()
    assert persist.await_args.args[1] == "first"
    assert persist.await_args.kwargs["tool_results"][0]["type"] == (
        "generation_cancelled"
    )


@pytest.mark.asyncio
async def test_chat_stream_closes_on_disconnect_and_persists_partial_content():
    handle = create_generation(user_id=1, conversation_id=2)

    async def fake_llm_stream(messages):
        yield "first"
        await asyncio.Event().wait()

    persist = AsyncMock(return_value=56)
    with patch.object(
        conversation_module,
        "chat_with_llm_stream",
        new=fake_llm_stream,
    ), patch.object(
        conversation_module,
        "_persist_assistant_message",
        new=persist,
    ):
        stream = conversation_module._stream_assistant_message(
            conversation_id=2,
            llm_messages=[],
            generation=handle,
        )
        assert (await anext(stream)) is not None  # start
        assert (await anext(stream)) is not None  # first delta

        # 模拟 GenerationStreamingResponse 检测到客户端断连后的 aclose。
        request_generation_cancel(handle, reason="client_disconnect")
        await stream.aclose()

    persist.assert_awaited_once()
    assert persist.await_args.args[1] == "first"
    assert persist.await_args.kwargs["tool_results"][0]["reason"] == (
        "client_disconnect"
    )


@pytest.mark.asyncio
async def test_agent_runtime_stops_between_tokens():
    handle = create_generation(user_id=1, conversation_id=2)
    runtime = AgentRuntime(ToolRegistry())
    context = AgentContext("system")
    context.add_user_message("question")

    async def fake_llm_stream(messages, tools):
        yield {"type": "text", "content": "first"}
        handle.cancel_event.set()
        yield {"type": "text", "content": "ignored"}

    with patch(
        "agent.runtime.chat_with_tools_stream",
        new=fake_llm_stream,
    ):
        events = [
            event
            async for event in runtime.run(
                context,
                cancel_event=handle.cancel_event,
            )
        ]

    assert [event["type"] for event in events] == [
        "agent_start",
        "text",
        "generation_cancelled",
    ]
    assert events[1]["content"] == "first"


@pytest.mark.asyncio
async def test_agent_service_persists_partial_content_on_cancel():
    handle = create_generation(user_id=1, conversation_id=2)

    class FakeRuntime:
        async def run(self, context, tool_names, cancel_event):
            yield {"type": "agent_start"}
            yield {"type": "text", "content": "first"}
            yield {"type": "generation_cancelled"}

    persist = AsyncMock(return_value=88)
    with patch.object(
        agent_service_module,
        "AgentRuntime",
        return_value=FakeRuntime(),
    ), patch.object(
        agent_service_module,
        "_persist_agent_message",
        new=persist,
    ):
        frames = [
            frame
            async for frame in agent_service_module.stream_agent_response(
                conversation_id=2,
                context=AgentContext("system"),
                generation=handle,
            )
        ]

    payloads = _sse_payloads(frames)
    assert [item["type"] for item in payloads] == [
        "agent_start",
        "text",
        "cancelled",
    ]
    assert payloads[0]["generation_id"] == handle.generation_id
    assert payloads[-1]["message_id"] == 88
    persist.assert_awaited_once()
    assert persist.await_args.args[1] == "first"


@pytest.mark.asyncio
async def test_rag_stream_stops_and_persists_partial_content():
    handle = create_generation(user_id=1, conversation_id=2)
    chunks = [
        {
            "content": "reference content",
            "document_id": 10,
            "chunk_index": 0,
            "page_number": 1,
            "score": 0.9,
        }
    ]

    async def fake_llm_stream(messages):
        yield "partial answer"
        handle.cancel_event.set()
        yield "ignored"

    persist = AsyncMock(return_value=77)
    with patch.object(
        rag_module,
        "run_retrieval_sync",
        new=AsyncMock(return_value=chunks),
    ), patch.object(
        rag_module,
        "_get_document_names",
        new=AsyncMock(return_value={10: "source.txt"}),
    ), patch.object(
        rag_module,
        "AsyncSessionLocal",
        return_value=_FakeSessionContext(),
    ), patch.object(
        rag_module,
        "chat_with_llm_stream",
        new=fake_llm_stream,
    ), patch.object(
        rag_module,
        "_persist_assistant_message",
        new=persist,
    ):
        frames = [
            frame
            async for frame in rag_module.rag_chat_stream(
                question="question",
                user_id=1,
                kb_id=3,
                conversation_id=2,
                generation=handle,
            )
        ]

    payloads = _sse_payloads(frames)
    assert [item["type"] for item in payloads] == [
        "start",
        "retrieval_start",
        "retrieval_result",
        "text",
        "cancelled",
    ]
    assert payloads[3]["content"] == "partial answer"
    assert payloads[-1]["message_id"] == 77
    persist.assert_awaited_once()
    assert persist.await_args.args[1] == "partial answer"
