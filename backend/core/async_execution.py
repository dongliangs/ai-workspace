from __future__ import annotations

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any, Callable, TypeVar

from core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 索引和检索使用独立线程池，避免大文档索引占满所有检索线程。
# max_workers 同时充当各链路的并发上限，超出的请求会在线程池队列中等待。
_index_executor = ThreadPoolExecutor(
    max_workers=settings.rag_index_concurrency,
    thread_name_prefix="rag-index",
)
_retrieval_executor = ThreadPoolExecutor(
    max_workers=settings.rag_retrieval_concurrency,
    thread_name_prefix="rag-retrieval",
)


async def _run_sync(
    executor: ThreadPoolExecutor,
    func: Callable[..., T],
    *args: Any,
    timeout_seconds: float,
    operation: str,
) -> T:
    # 把同步函数交给线程执行，当前线程会 await 在这里让出事件循环，
    # 因此其他请求仍能被 FastAPI 调度。
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(executor, functools.partial(func, *args))
    started_at = perf_counter()

    try:
        # wait_for 只取消“等待结果”的 Future，不能强制终止已经运行的
        # Python 线程；线程池的 max_workers 仍会限制实际并发任务数。
        result = await asyncio.wait_for(future, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error(
            "%s timed out after %.1f seconds",
            operation,
            timeout_seconds,
        )
        raise TimeoutError(
            f"{operation} exceeded the {timeout_seconds:.1f}s timeout"
        ) from None
    except Exception:
        logger.exception("%s failed", operation)
        raise

    logger.debug(
        "%s completed in %.3f seconds",
        operation,
        perf_counter() - started_at,
    )
    return result


async def run_index_sync(
    func: Callable[..., T],
    *args: Any,
    timeout_seconds: float | None = None,
    operation: str | None = None,
) -> T:
    """在索引线程池中执行同步操作，避免阻塞 FastAPI 事件循环。"""
    return await _run_sync(
        _index_executor,
        func,
        *args,
        timeout_seconds=timeout_seconds or settings.rag_index_timeout_seconds,
        operation=operation or getattr(func, "__name__", repr(func)),
    )


async def run_retrieval_sync(
    func: Callable[..., T],
    *args: Any,
    timeout_seconds: float | None = None,
    operation: str | None = None,
) -> T:
    """在检索线程池中执行同步操作，避免阻塞 FastAPI 事件循环。"""
    return await _run_sync(
        _retrieval_executor,
        func,
        *args,
        timeout_seconds=timeout_seconds or settings.rag_retrieval_timeout_seconds,
        operation=operation or getattr(func, "__name__", repr(func)),
    )


def shutdown_executors() -> None:
    """应用关闭时取消排队任务，并释放索引和检索线程池。"""
    _index_executor.shutdown(wait=False, cancel_futures=True)
    _retrieval_executor.shutdown(wait=False, cancel_futures=True)
