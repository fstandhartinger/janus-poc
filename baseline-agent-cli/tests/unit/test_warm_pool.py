"""Tests for warm pool management."""

import asyncio
import time

import pytest

from janus_baseline_agent_cli.services.warm_pool import WarmPoolManager


class FakeSandyService:
    def __init__(self) -> None:
        self._available = True
        self._counter = 0
        self.terminated: list[str] = []
        self.reset_calls: list[str] = []

    @property
    def is_available(self) -> bool:
        return self._available

    async def prepare_warm_sandbox(self):
        self._counter += 1
        return f"sandbox-{self._counter}", None

    async def check_sandbox(self, sandbox_id: str) -> bool:
        return True

    async def terminate(self, sandbox_id: str) -> None:
        self.terminated.append(sandbox_id)

    async def reset_sandbox(self, sandbox_id: str) -> None:
        self.reset_calls.append(sandbox_id)


async def _wait_for_pool_size(
    pool: WarmPoolManager, target: int, timeout: float = 1.0
) -> None:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if pool.size == target:
            return
        await asyncio.sleep(0.01)
    assert pool.size == target


@pytest.mark.asyncio
async def test_warm_pool_acquisition() -> None:
    sandy = FakeSandyService()
    pool = WarmPoolManager(
        sandy,
        pool_size=2,
        maintenance_interval=3600,
        refill_on_acquire=False,
    )
    await pool.start()

    assert pool.size == 2

    sandbox = await pool.acquire()
    assert sandbox is not None

    await pool.release(sandbox, reusable=True)
    assert pool.size == 2

    await pool.stop()


@pytest.mark.asyncio
async def test_sandbox_recycling() -> None:
    sandy = FakeSandyService()
    pool = WarmPoolManager(
        sandy,
        pool_size=1,
        maintenance_interval=3600,
        refill_on_acquire=False,
    )
    await pool.start()

    sandbox = await pool.acquire()
    assert sandbox is not None

    await pool.release(sandbox, reusable=True)
    sandbox2 = await pool.acquire()
    assert sandbox2 is not None
    assert sandbox2.sandbox_id == sandbox.sandbox_id

    await pool.stop()


@pytest.mark.asyncio
async def test_warm_pool_refill_on_acquire() -> None:
    sandy = FakeSandyService()
    pool = WarmPoolManager(
        sandy,
        pool_size=2,
        maintenance_interval=3600,
    )
    await pool.start()

    sandbox = await pool.acquire()
    assert sandbox is not None
    assert pool.size == 1

    await _wait_for_pool_size(pool, 2)

    await pool.release(sandbox, reusable=True)
    assert pool.size == 2

    await pool.stop()
