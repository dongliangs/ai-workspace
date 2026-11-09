from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from time import monotonic


class CircuitState(str, Enum):
    """熔断器状态。

    CLOSED:
        正常放行请求。连续失败达到阈值后进入 OPEN。
    OPEN:
        快速失败，不继续请求上游服务，避免故障期间持续堆积连接。
    HALF_OPEN:
        冷却时间结束后只允许少量探测请求通过。探测成功则恢复，
        探测失败则重新进入 OPEN。
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """熔断器处于打开状态时抛出的异常。"""

    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = max(0.0, retry_after_seconds)
        super().__init__(
            f"LLM 服务熔断中，请在 {self.retry_after_seconds:.0f} 秒后重试"
        )


@dataclass(frozen=True)
class CircuitPermit:
    """一次受熔断器保护的调用凭证。

    epoch 用于识别调用开始时熔断器的状态版本。若调用期间熔断器已经
    发生状态切换，迟到的成功/失败结果会被忽略，避免旧请求污染新状态。
    """

    epoch: int
    is_half_open_probe: bool


class CircuitBreaker:
    """适用于单个上游依赖的异步熔断器。

    实现说明：
    - 所有状态读写都放在 asyncio.Lock 内，适配多协程并发场景；
    - 只在一次完整的“重试后调用”结束时记录一次结果，避免一次请求
      的重试次数把熔断阈值快速打满；
    - HALF_OPEN 状态最多放行 half_open_max_calls 个探测请求；
    - 客户端主动取消或断连不属于上游故障，只释放半开探测名额，
      不增加失败计数。
    """

    def __init__(
        self,
        *,
        name: str,
        failure_threshold: int,
        recovery_timeout_seconds: float,
        half_open_max_calls: int = 1,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold 必须大于等于 1")
        if recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds 必须大于 0")
        if half_open_max_calls < 1:
            raise ValueError("half_open_max_calls 必须大于等于 1")

        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = 0.0
        self._half_open_in_flight = 0
        self._epoch = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """返回当前状态，供日志、监控和测试读取。"""
        return self._state

    @property
    def failure_count(self) -> int:
        """返回连续失败次数。"""
        return self._failure_count

    async def acquire(self) -> CircuitPermit:
        """申请一次调用许可。

        熔断器打开且仍在冷却期时立即抛出 CircuitOpenError，让业务层
        快速返回友好提示，而不是等待连接超时。
        """
        async with self._lock:
            now = monotonic()

            if self._state is CircuitState.OPEN:
                elapsed = now - self._opened_at
                if elapsed < self.recovery_timeout_seconds:
                    raise CircuitOpenError(
                        self.recovery_timeout_seconds - elapsed
                    )

                # 冷却期结束，进入半开状态。此时只发放少量探测许可，
                # 其他并发请求仍会快速失败，防止恢复瞬间流量洪峰。
                self._state = CircuitState.HALF_OPEN
                self._half_open_in_flight = 0
                self._epoch += 1

            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_in_flight >= self.half_open_max_calls:
                    raise CircuitOpenError(
                        self.recovery_timeout_seconds
                    )
                self._half_open_in_flight += 1
                return CircuitPermit(
                    epoch=self._epoch,
                    is_half_open_probe=True,
                )

            return CircuitPermit(
                epoch=self._epoch,
                is_half_open_probe=False,
            )

    async def record_success(self, permit: CircuitPermit) -> None:
        """记录一次完整调用成功。

        CLOSED 状态下成功会清零连续失败数；HALF_OPEN 下探测成功
        会关闭熔断器，恢复正常流量。
        """
        async with self._lock:
            if permit.epoch != self._epoch:
                return

            if self._state is CircuitState.HALF_OPEN and permit.is_half_open_probe:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_in_flight = 0
                self._epoch += 1
                return

            if self._state is CircuitState.CLOSED:
                self._failure_count = 0

    async def record_failure(self, permit: CircuitPermit) -> None:
        """记录一次完整调用最终失败（已经用完重试次数）。"""
        async with self._lock:
            if permit.epoch != self._epoch:
                return

            if self._state is CircuitState.HALF_OPEN and permit.is_half_open_probe:
                self._open_locked()
                return

            if self._state is CircuitState.CLOSED and not permit.is_half_open_probe:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._open_locked()

    async def record_cancelled(self, permit: CircuitPermit) -> None:
        """记录调用被取消。

        用户断连或任务取消不能算作上游失败；这里只归还 HALF_OPEN
        探测名额，避免熔断器永久卡在“探测已占用”的状态。
        """
        async with self._lock:
            if permit.epoch != self._epoch:
                return
            if self._state is CircuitState.HALF_OPEN and permit.is_half_open_probe:
                self._half_open_in_flight = max(
                    0,
                    self._half_open_in_flight - 1,
                )

    async def reset(self) -> None:
        """重置熔断器，主要供应用测试和人工恢复操作使用。"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = 0.0
            self._half_open_in_flight = 0
            self._epoch += 1

    def _open_locked(self) -> None:
        """在已经持有锁的情况下切换到 OPEN 状态。"""
        self._state = CircuitState.OPEN
        self._opened_at = monotonic()
        self._half_open_in_flight = 0
        self._epoch += 1
