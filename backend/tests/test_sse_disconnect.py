import asyncio

import pytest

from api.sse import GenerationStreamingResponse
from services.generation_manager import (
    create_generation,
    get_generation_cancel_reason,
    is_generation_finished,
    request_generation_cancel,
)


@pytest.mark.asyncio
async def test_disconnect_marks_generation_and_closes_stream():
    generation = create_generation(user_id=1, conversation_id=2)
    closed_event = asyncio.Event()

    async def stream():
        try:
            yield b"data: first\n\n"
            await asyncio.Event().wait()
        finally:
            closed_event.set()

    body = stream()
    response = GenerationStreamingResponse(body, generation=generation)

    # 先消费一帧，模拟 SSE 已经开始向客户端发送。
    assert await anext(response.body_iterator) == b"data: first\n\n"

    await response._handle_disconnect()

    assert get_generation_cancel_reason(generation) == "client_disconnect"
    assert is_generation_finished(generation) is False
    assert closed_event.is_set() is True


@pytest.mark.asyncio
async def test_disconnect_does_not_override_user_cancel_reason():
    generation = create_generation(user_id=1, conversation_id=2)
    request_generation_cancel(generation, reason="user")

    async def stream():
        yield b"data: first\n\n"

    response = GenerationStreamingResponse(stream(), generation=generation)
    await anext(response.body_iterator)
    await response._handle_disconnect()

    assert get_generation_cancel_reason(generation) == "user"


def test_streaming_response_exposes_generation_id_header():
    generation = create_generation(user_id=1, conversation_id=2)

    async def stream():
        if False:
            yield b""

    response = GenerationStreamingResponse(stream(), generation=generation)

    assert response.media_type == "text/event-stream"
    assert response.headers["x-generation-id"] == generation.generation_id
