# services/llm_service.py
"""
LLM 调用统一封装。

本模块集中处理以下可靠性问题，业务层只关心文本/事件结果：
1. 单次 LLM 请求超时；
2. 流式响应空闲超时和总时长超时；
3. 连接失败、限流和 5xx 的指数退避重试；
4. 连续故障后的熔断与半开恢复；
5. 流式调用开始输出后不再重试，避免前端收到重复文本。
"""

from __future__ import annotations

import asyncio
import logging
import random
from time import monotonic
from typing import Any, AsyncIterator, Awaitable, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from core.circuit_breaker import CircuitBreaker, CircuitPermit
from core.config import settings

logger = logging.getLogger(__name__)


class LLMServiceUnavailableError(RuntimeError):
    """LLM 在超时、重试和熔断处理后仍不可用。

    对外只暴露稳定的友好提示，具体上游异常保留在异常链和日志中，
    避免把供应商地址、鉴权信息或内部堆栈返回给前端。
    """

    public_message = "AI 服务暂时不可用，请稍后重试"

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(self.public_message)


# 创建 OpenAI 异步客户端。
# max_retries=0 是有意设置：SDK 自带重试无法与我们的熔断统计、日志和
# “首帧后禁止重试”策略统一，因此这里完全由本模块控制重试次数。
_client_options: dict[str, Any] = {
    "api_key": settings.deepseek_api_key,
    "timeout": max(
        settings.llm_request_timeout_seconds,
        settings.llm_stream_total_timeout_seconds,
    ),
    "max_retries": 0,
}
if settings.deepseek_base_url:
    _client_options["base_url"] = settings.deepseek_base_url

client = AsyncOpenAI(**_client_options)


# 熔断器是进程级共享状态：所有普通对话、Agent 和 RAG 请求共同保护
# 同一个 DeepSeek 上游。多进程部署时需要把状态迁移到 Redis 等共享存储。
_llm_circuit_breaker = CircuitBreaker(
    name="deepseek",
    failure_threshold=settings.llm_circuit_failure_threshold,
    recovery_timeout_seconds=settings.llm_circuit_recovery_timeout_seconds,
    half_open_max_calls=settings.llm_circuit_half_open_max_calls,
)


def get_llm_circuit_breaker() -> CircuitBreaker:
    """返回当前 LLM 熔断器，便于监控和测试读取状态。"""
    return _llm_circuit_breaker


def _is_retryable_error(exc: BaseException) -> bool:
    """判断异常是否属于可安全重试的瞬时上游故障。

    - 连接失败、连接超时、读写超时通常由网络抖动引起；
    - 408/409/425/429 表示请求暂未成功，可退避后重试；
    - 5xx 表示上游服务临时异常；
    - 400/401/403/404 等客户端或配置错误不重试，避免放大错误请求。
    """
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        status_code = getattr(exc, "status_code", 0)
        return status_code in {408, 409, 425, 429} or status_code >= 500
    return False


def _retry_after_seconds(exc: BaseException) -> float | None:
    """读取上游 Retry-After 响应头，存在时优先遵循服务端建议。"""
    if not isinstance(exc, APIStatusError):
        return None

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        # Retry-After 也允许 HTTP 日期格式。这里不引入日期解析复杂度，
        # 直接回退到本地指数退避，避免因异常头格式影响重试流程。
        return None


async def _sleep_before_retry(
    *,
    operation: str,
    retry_index: int,
    exc: BaseException,
) -> None:
    """按指数退避等待后重试。

    retry_index 从 0 开始，等待时间为：
        min(最大等待, 基础等待 * 2^retry_index)
    再叠加 50% 范围内的随机抖动，避免多个请求在故障恢复瞬间同时重试。
    """
    base_delay = settings.llm_retry_base_delay_seconds * (2 ** retry_index)
    delay = min(settings.llm_retry_max_delay_seconds, base_delay)
    server_delay = _retry_after_seconds(exc)
    if server_delay is not None:
        delay = min(settings.llm_retry_max_delay_seconds, server_delay)
    else:
        delay *= 0.5 + random.random() * 0.5

    logger.warning(
        "%s 第 %d 次调用失败，将在 %.3f 秒后重试: %s",
        operation,
        retry_index + 1,
        delay,
        exc,
    )
    if delay > 0:
        await asyncio.sleep(delay)


async def _record_cancelled_safely(
    permit: CircuitPermit | None,
) -> None:
    """客户端取消时归还熔断器半开许可，且不让清理动作覆盖原异常。"""
    if permit is None:
        return
    try:
        await _llm_circuit_breaker.record_cancelled(permit)
    except Exception:
        # 熔断器记录失败不能影响断连清理和取消异常向上传播。
        logger.exception("记录 LLM 取消状态失败")


async def _close_stream(stream: Any | None) -> None:
    """关闭 OpenAI 流并释放连接。

    OpenAI 的 AsyncStream 使用 close()，普通异步生成器使用 aclose()。
    两种形式都兼容，清理异常只记录日志，不覆盖真正的业务异常。
    """
    if stream is None:
        return

    close_method = getattr(stream, "close", None)
    if close_method is None:
        close_method = getattr(stream, "aclose", None)
    if close_method is None:
        return

    try:
        result = close_method()
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        logger.exception("关闭 LLM 上游流失败")


async def _wait_for_request(
    awaitable: Awaitable[Any],
    *,
    operation: str,
) -> Any:
    """为单次请求建立超时边界，并把底层超时统一成标准异常。"""
    try:
        return await asyncio.wait_for(
            awaitable,
            timeout=settings.llm_request_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise TimeoutError(
            f"{operation} 超过 {settings.llm_request_timeout_seconds:.1f} 秒"
        ) from exc


async def chat_with_tools(messages: list[dict], tools: list[dict]):
    """
    调用 LLM（Chat Completions API），携带工具定义，返回完整响应。

    用于 Agent Loop：模型可以返回文本，也可以返回 tool_calls。
    本函数在一条完整调用级别执行重试和熔断统计，任意一次成功都会
    清零连续失败计数。
    """
    operation = "chat_with_tools"

    # 熔断许可在开始调用前申请。若熔断器已经打开，这里会立即失败，
    # 不会真正向 DeepSeek 发起网络请求。
    permit = await _llm_circuit_breaker.acquire()
    max_attempts = settings.llm_max_retries + 1

    try:
        for attempt in range(max_attempts):
            try:
                response = await _wait_for_request(
                    client.chat.completions.create(
                        model=settings.deepseek_model,
                        messages=messages,
                        tools=tools if tools else None,
                    ),
                    operation=operation,
                )
                await _llm_circuit_breaker.record_success(permit)
                return response
            except Exception as exc:
                can_retry = (
                    _is_retryable_error(exc)
                    and attempt < max_attempts - 1
                )
                if can_retry:
                    await _sleep_before_retry(
                        operation=operation,
                        retry_index=attempt,
                        exc=exc,
                    )
                    continue

                await _llm_circuit_breaker.record_failure(permit)
                logger.exception("%s 调用最终失败", operation)
                raise LLMServiceUnavailableError(operation) from exc
    except (asyncio.CancelledError, GeneratorExit):
        # 任务取消不是上游故障，不能计入熔断失败次数。
        await _record_cancelled_safely(permit)
        raise

    # 理论上循环总会 return 或 raise；保留兜底便于静态分析和防御式处理。
    await _llm_circuit_breaker.record_failure(permit)
    raise LLMServiceUnavailableError(operation)


async def _stream_with_resilience(
    *,
    operation: str,
    request_factory: Callable[[], Awaitable[Any]],
    parse_chunk: Callable[[Any], list[dict[str, Any]]],
) -> AsyncIterator[dict[str, Any]]:
    """带超时、重试和熔断的统一流式调用器。

    重试边界：
    - 只有尚未向业务层 yield 任何事件时才允许重试；
    - 一旦首帧已经输出，后续网络错误只能结束本次生成，不能重新请求，
      否则前端会看到重复文本或重复工具调用。

    超时边界：
    - 建立流式连接受 llm_request_timeout_seconds 限制；
    - 两次数据片之间受 llm_stream_idle_timeout_seconds 限制；
    - 整个生成过程受 llm_stream_total_timeout_seconds 限制。
    """
    permit = await _llm_circuit_breaker.acquire()
    max_attempts = settings.llm_max_retries + 1
    emitted_any_event = False
    deadline = monotonic() + settings.llm_stream_total_timeout_seconds

    try:
        for attempt in range(max_attempts):
            stream: Any | None = None
            try:
                stream = await _wait_for_request(
                    request_factory(),
                    operation=operation,
                )
                iterator = stream.__aiter__()

                while True:
                    remaining_total = deadline - monotonic()
                    if remaining_total <= 0:
                        raise TimeoutError(
                            f"{operation} 超过总时长 "
                            f"{settings.llm_stream_total_timeout_seconds:.1f} 秒"
                        )

                    per_chunk_timeout = min(
                        settings.llm_stream_idle_timeout_seconds,
                        remaining_total,
                    )
                    try:
                        chunk = await asyncio.wait_for(
                            anext(iterator),
                            timeout=per_chunk_timeout,
                        )
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError as exc:
                        raise TimeoutError(
                            f"{operation} 超过 "
                            f"{per_chunk_timeout:.1f} 秒未收到新数据"
                        ) from exc

                    for event in parse_chunk(chunk):
                        emitted_any_event = True
                        yield event

                await _llm_circuit_breaker.record_success(permit)
                return
            except Exception as exc:
                # 先关闭失败连接，避免半截 HTTP 流继续占用连接池。
                await _close_stream(stream)

                can_retry = (
                    not emitted_any_event
                    and _is_retryable_error(exc)
                    and attempt < max_attempts - 1
                )
                if can_retry:
                    await _sleep_before_retry(
                        operation=operation,
                        retry_index=attempt,
                        exc=exc,
                    )
                    continue

                await _llm_circuit_breaker.record_failure(permit)
                logger.exception("%s 流式调用最终失败", operation)
                raise LLMServiceUnavailableError(operation) from exc
            finally:
                await _close_stream(stream)
    except (asyncio.CancelledError, GeneratorExit):
        # SSE 客户端断连会触发 GeneratorExit 或 CancelledError。此处只
        # 释放熔断器探测名额，不把客户端行为算成上游服务故障。
        await _record_cancelled_safely(permit)
        raise

    await _llm_circuit_breaker.record_failure(permit)
    raise LLMServiceUnavailableError(operation)


def _parse_chat_tool_chunk(chunk: Any) -> list[dict[str, Any]]:
    """把 Chat Completions 流式分片转换为业务事件列表。"""
    if not getattr(chunk, "choices", None):
        return []

    delta = chunk.choices[0].delta
    if delta is None:
        return []

    events: list[dict[str, Any]] = []
    if delta.content:
        events.append({"type": "text", "content": delta.content})

    if delta.tool_calls:
        for tool_call in delta.tool_calls:
            function = tool_call.function
            events.append({
                "type": "tool_call_delta",
                "index": tool_call.index,
                "id": tool_call.id,
                "name": function.name if function else None,
                "arguments": function.arguments if function else None,
            })
    return events


def _parse_responses_text_chunk(chunk: Any) -> list[dict[str, Any]]:
    """把 Responses API 的文本增量事件转换为内部统一事件。"""
    if getattr(chunk, "type", None) != "response.output_text.delta":
        return []
    delta = getattr(chunk, "delta", None)
    if not delta:
        return []
    return [{"type": "text", "content": delta}]


async def chat_with_tools_stream(
    messages: list[dict],
    tools: list[dict],
) -> AsyncIterator[dict[str, Any]]:
    """
    流式调用 LLM（Chat Completions API），携带工具定义。

    Yields:
        - {"type": "text", "content": "..."} 文本增量；
        - {"type": "tool_call_delta", ...} 工具调用增量碎片。
    """
    async for event in _stream_with_resilience(
        operation="chat_with_tools_stream",
        request_factory=lambda: client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            tools=tools if tools else None,
            stream=True,
        ),
        parse_chunk=_parse_chat_tool_chunk,
    ):
        yield event


async def chat_with_llm_stream(
    messages: list[dict],
) -> AsyncIterator[str]:
    """
    调用 LLM，流式返回文本块（async generator，逐段 yield str 增量）。

    业务层保持原有接口不变；底层自动获得超时、重试和熔断能力。
    """
    async for event in _stream_with_resilience(
        operation="chat_with_llm_stream",
        request_factory=lambda: client.responses.create(
            model=settings.deepseek_model,
            input=messages,
            stream=True,
        ),
        parse_chunk=_parse_responses_text_chunk,
    ):
        yield event["content"]
