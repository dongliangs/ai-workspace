"""SSE 响应封装：统一处理客户端断连和生成任务清理。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterable, Awaitable, Callable

from starlette.requests import ClientDisconnect
from starlette.responses import StreamingResponse

from services.generation_manager import (
    GenerationHandle,
    is_generation_finished,
    request_generation_cancel,
)

logger = logging.getLogger(__name__)


class GenerationStreamingResponse(StreamingResponse):
    """带生成生命周期的 SSE 响应。

    为什么不直接在业务生成器里轮询 request.is_disconnected()：
    Starlette 的 StreamingResponse 已经在后台监听 ASGI 的 http.disconnect
    事件。两个消费者同时读取 receive() 会竞争同一个 ASGI 消息，可能导致
    响应层漏掉断连事件。因此这里复用 Starlette 的断连检测，只在响应
    退出时补充“标记取消原因 + 主动关闭业务异步生成器”两步。

    这样可以保证客户端关闭页面、刷新连接或网络断开时：
    1. 生成任务被标记为 client_disconnect；
    2. 上游 LLM 流的 finally 逻辑尽快执行并释放 HTTP 连接；
    3. 已经生成的部分内容有机会在服务层 finally 中持久化；
    4. 活动生成注册表不会因断连而泄漏。
    """

    def __init__(
        self,
        content: AsyncIterable[bytes],
        *,
        generation: GenerationHandle,
        status_code: int = 200,
    ) -> None:
        headers = {
            # 禁止浏览器和常见反向代理缓存 SSE 内容。
            "Cache-Control": "no-cache",
            # Nginx 等代理需要该响应头才会实时转发每一帧。
            "X-Accel-Buffering": "no",
            # 响应头和 start 事件都携带 ID，兼容无法读取自定义响应头的客户端。
            "X-Generation-ID": generation.generation_id,
        }
        super().__init__(
            content=content,
            status_code=status_code,
            media_type="text/event-stream",
            headers=headers,
        )
        self.generation = generation
        self._disconnect_handled = False

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """执行 SSE 响应，并在断连或取消时完成清理。"""
        try:
            await super().__call__(scope, receive, send)
        except (asyncio.CancelledError, ClientDisconnect):
            # Starlette 检测到 http.disconnect 后，在部分 ASGI 版本中会
            # 取消响应任务，而不是正常 return；显式记录后继续向上抛出，
            # 不吞掉服务器的取消信号。
            await self._handle_disconnect()
            raise
        finally:
            # 兼容没有在断连时抛异常的 ASGI 版本。只要业务生成器没有
            # 走到 done/error/cancelled 终止路径，就视为客户端提前断开。
            if not is_generation_finished(self.generation):
                await self._handle_disconnect()

    async def _handle_disconnect(self) -> None:
        """标记断连并关闭业务异步生成器。"""
        if self._disconnect_handled or is_generation_finished(self.generation):
            return
        self._disconnect_handled = True

        # 只记录第一次原因。如果用户先点击“停止生成”，随后连接才关闭，
        # 这里会保留更准确的 user 原因。
        request_generation_cancel(
            self.generation,
            reason="client_disconnect",
        )

        close_method = getattr(self.body_iterator, "aclose", None)
        if close_method is None:
            return

        try:
            # aclose 会向业务生成器注入 GeneratorExit，触发其中的 finally
            # 块关闭上游 LLM 流并保存部分内容。shield 防止响应任务当前
            # 的取消信号立刻打断清理动作。
            await asyncio.shield(close_method())
        except asyncio.CancelledError:
            # 清理已经由 shield 内部任务继续执行；这里不吞掉外层取消。
            raise
        except Exception:
            logger.exception(
                "关闭断连 SSE 生成器失败 generation_id=%s",
                self.generation.generation_id,
            )
