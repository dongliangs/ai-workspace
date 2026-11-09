import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import services.llm_service as llm_module
from core.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from services.llm_service import LLMServiceUnavailableError


def _new_breaker(
    *,
    failure_threshold: int = 1,
    recovery_timeout_seconds: float = 0.02,
) -> CircuitBreaker:
    return CircuitBreaker(
        name="test-llm",
        failure_threshold=failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds,
    )


def _fast_retry_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试中关闭真实等待时间，只验证重试行为本身。"""
    monkeypatch.setattr(llm_module.settings, "llm_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(llm_module.settings, "llm_retry_max_delay_seconds", 0.0)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers_after_probe():
    breaker = _new_breaker(failure_threshold=2, recovery_timeout_seconds=0.02)

    first = await breaker.acquire()
    await breaker.record_failure(first)
    second = await breaker.acquire()
    await breaker.record_failure(second)

    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await breaker.acquire()

    await asyncio.sleep(0.03)
    probe = await breaker.acquire()
    assert probe.is_half_open_probe is True
    assert breaker.state is CircuitState.HALF_OPEN

    # 半开状态只允许一个探测请求，其他并发请求应快速失败。
    with pytest.raises(CircuitOpenError):
        await breaker.acquire()

    await breaker.record_success(probe)
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_non_stream_call_retries_and_then_succeeds(monkeypatch):
    _fast_retry_settings(monkeypatch)
    monkeypatch.setattr(llm_module, "_llm_circuit_breaker", _new_breaker())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 2)

    response = object()
    create = AsyncMock(side_effect=[TimeoutError("temporary"), response])
    monkeypatch.setattr(
        llm_module.client.chat.completions,
        "create",
        create,
    )

    assert await llm_module.chat_with_tools([], []) is response
    assert create.await_count == 2
    assert llm_module._llm_circuit_breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_final_failure_opens_circuit_and_blocks_next_call(monkeypatch):
    _fast_retry_settings(monkeypatch)
    breaker = _new_breaker(failure_threshold=1)
    monkeypatch.setattr(llm_module, "_llm_circuit_breaker", breaker)
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 0)

    create = AsyncMock(side_effect=TimeoutError("upstream timeout"))
    monkeypatch.setattr(
        llm_module.client.chat.completions,
        "create",
        create,
    )

    with pytest.raises(LLMServiceUnavailableError):
        await llm_module.chat_with_tools([], [])

    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await llm_module.chat_with_tools([], [])

    # 第二次调用被熔断器直接拦截，不应继续访问上游客户端。
    assert create.await_count == 1


@pytest.mark.asyncio
async def test_stream_retries_when_failure_happens_before_first_event(monkeypatch):
    _fast_retry_settings(monkeypatch)
    monkeypatch.setattr(llm_module, "_llm_circuit_breaker", _new_breaker())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 1)

    async def failing_stream():
        raise TimeoutError("connection not ready")
        yield  # pragma: no cover - 仅用于声明异步生成器

    async def successful_stream():
        yield SimpleNamespace(
            type="response.output_text.delta",
            delta="hello",
        )

    create = AsyncMock(side_effect=[failing_stream(), successful_stream()])
    monkeypatch.setattr(llm_module.client.responses, "create", create)

    chunks = [chunk async for chunk in llm_module.chat_with_llm_stream([])]

    assert chunks == ["hello"]
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_stream_never_retries_after_first_event(monkeypatch):
    _fast_retry_settings(monkeypatch)
    monkeypatch.setattr(llm_module, "_llm_circuit_breaker", _new_breaker())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 3)

    async def partially_failing_stream():
        yield SimpleNamespace(
            type="response.output_text.delta",
            delta="first",
        )
        raise TimeoutError("stream broke after output")

    async def should_not_be_used():
        yield SimpleNamespace(
            type="response.output_text.delta",
            delta="duplicate",
        )

    create = AsyncMock(
        side_effect=[partially_failing_stream(), should_not_be_used()]
    )
    monkeypatch.setattr(llm_module.client.responses, "create", create)

    chunks: list[str] = []
    with pytest.raises(LLMServiceUnavailableError):
        async for chunk in llm_module.chat_with_llm_stream([]):
            chunks.append(chunk)

    # 已经输出过 first 后不能再次请求，否则会产生重复内容。
    assert chunks == ["first"]
    assert create.await_count == 1


@pytest.mark.asyncio
async def test_stream_idle_timeout_is_reported(monkeypatch):
    _fast_retry_settings(monkeypatch)
    monkeypatch.setattr(llm_module, "_llm_circuit_breaker", _new_breaker())
    monkeypatch.setattr(llm_module.settings, "llm_max_retries", 0)
    monkeypatch.setattr(llm_module.settings, "llm_stream_idle_timeout_seconds", 0.01)
    monkeypatch.setattr(llm_module.settings, "llm_stream_total_timeout_seconds", 1.0)

    class SlowStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            await asyncio.sleep(0.05)
            raise StopAsyncIteration

        async def close(self):
            return None

    create = AsyncMock(return_value=SlowStream())
    monkeypatch.setattr(llm_module.client.responses, "create", create)

    with pytest.raises(LLMServiceUnavailableError):
        async for _ in llm_module.chat_with_llm_stream([]):
            pass

    assert create.await_count == 1
