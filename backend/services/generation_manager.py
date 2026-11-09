import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GenerationHandle:
    """一次正在执行的生成任务句柄。"""

    generation_id: str
    user_id: int
    conversation_id: int
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # 取消原因用于区分用户主动停止、SSE 客户端断连和上游生成异常。
    # 它只记录第一次取消原因，后续清理不会覆盖更准确的业务原因。
    cancel_reason: str | None = None
    # 是否已经正常走到 done/error/cancelled 等终止路径。
    # 响应层据此判断生成器是否在完成前被客户端提前关闭。
    finished: bool = False


# 当前部署是单进程，任务句柄可以直接保存在内存中。
# 多 worker 部署时，需要改用 Redis Pub/Sub 或其他跨进程取消机制。
_active_generations: dict[str, GenerationHandle] = {}


def create_generation(user_id: int, conversation_id: int) -> GenerationHandle:
    """注册一次新的生成任务，并生成不可预测的外部生成 ID。"""
    handle = GenerationHandle(
        generation_id=uuid.uuid4().hex,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    _active_generations[handle.generation_id] = handle
    return handle


def cancel_generation(
    generation_id: str,
    user_id: int,
) -> GenerationHandle | None:
    """校验归属后设置取消信号；不属于当前用户时返回 None。"""
    handle = _active_generations.get(generation_id)
    if handle is None or handle.user_id != user_id:
        return None

    request_generation_cancel(handle, reason="user")
    return handle


def request_generation_cancel(
    handle: GenerationHandle,
    *,
    reason: str,
) -> bool:
    """请求停止生成，并记录第一次触发取消的原因。

    返回值表示本次调用是否真正改变了取消原因。重复请求（例如用户点击
    停止后网络又断开）会保留最早的原因，避免日志和持久化信息来回变化。
    """
    if handle.finished:
        return False

    changed = handle.cancel_reason is None
    if changed:
        handle.cancel_reason = reason
    # 即使原因已经存在，也要确保事件处于 set 状态，便于所有等待方
    # 通过同一个 cancel_event 协作式退出。
    handle.cancel_event.set()
    return changed


def mark_generation_finished(handle: GenerationHandle) -> None:
    """标记生成已经走到业务终止路径。

    该函数应在发送 done/error/cancelled 终止帧之前调用。响应层只有在
    finished=False 时才会把生成器关闭识别为“客户端提前断连”。
    """
    handle.finished = True


def is_generation_finished(handle: GenerationHandle) -> bool:
    """返回生成是否已经自然进入终止路径。"""
    return handle.finished


def get_generation_cancel_reason(handle: GenerationHandle) -> str | None:
    """返回第一次记录的取消原因。"""
    return handle.cancel_reason


def remove_generation(handle: GenerationHandle) -> None:
    """流式任务结束后移除句柄，避免内存持续增长。"""
    current = _active_generations.get(handle.generation_id)
    if current is handle:
        _active_generations.pop(handle.generation_id, None)


def is_generation_cancelled(handle: GenerationHandle) -> bool:
    """判断用户是否已经请求停止生成。"""
    return handle.cancel_event.is_set()
