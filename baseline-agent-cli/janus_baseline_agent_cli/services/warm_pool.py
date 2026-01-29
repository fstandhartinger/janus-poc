"""Warm pool management for pre-warmed Sandy sandboxes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import structlog

from janus_baseline_agent_cli.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from janus_baseline_agent_cli.services.debug import DebugEmitter
from janus_baseline_agent_cli.services.sandy import SandyService

logger = structlog.get_logger()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WarmSandbox:
    """A pre-warmed sandbox ready for use."""

    sandbox_id: str
    public_url: str | None
    created_at: datetime
    sandy_service: SandyService
    last_used: datetime | None = None
    request_count: int = 0
    last_error: bool = False
    last_exit_code: int = 0
    last_artifacts: bool = False
    termination_scheduled: bool = False

    async def stream(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Stream a request using this sandbox."""
        self.last_used = _utcnow()
        self.request_count += 1
        run_state: dict[str, Any] = {}
        async for chunk in self.sandy_service.execute_via_agent_api_in_sandbox(
            sandbox_id=self.sandbox_id,
            public_url=self.public_url,
            request=request,
            debug_emitter=debug_emitter,
            baseline_agent_override=baseline_agent_override,
            run_state=run_state,
            terminate_on_finish=False,
        ):
            yield chunk
        self._apply_run_state(run_state)

    async def complete(
        self,
        request: ChatCompletionRequest,
        debug_emitter: DebugEmitter | None = None,
        baseline_agent_override: str | None = None,
    ) -> ChatCompletionResponse:
        """Run a non-streaming request using this sandbox."""
        self.last_used = _utcnow()
        self.request_count += 1
        run_state: dict[str, Any] = {}
        response = await self.sandy_service.complete_via_agent_api_in_sandbox(
            sandbox_id=self.sandbox_id,
            public_url=self.public_url,
            request=request,
            debug_emitter=debug_emitter,
            baseline_agent_override=baseline_agent_override,
            run_state=run_state,
            terminate_on_finish=False,
        )
        self._apply_run_state(run_state)
        return response

    async def reset(self) -> None:
        """Reset sandbox state for reuse."""
        await self.sandy_service.reset_sandbox(self.sandbox_id)

    async def terminate(self) -> None:
        """Terminate the sandbox."""
        await self.sandy_service.terminate(self.sandbox_id)

    def is_reusable(self) -> bool:
        """Return whether the sandbox is eligible for reuse."""
        return not (self.last_error or self.last_artifacts or self.termination_scheduled)

    def _apply_run_state(self, run_state: dict[str, Any]) -> None:
        self.last_error = bool(run_state.get("has_error"))
        self.last_exit_code = int(run_state.get("exit_code") or 0)
        self.last_artifacts = bool(run_state.get("artifacts_present"))
        self.termination_scheduled = bool(run_state.get("termination_scheduled"))


class WarmPoolManager:
    """Manages a pool of pre-warmed Sandy sandboxes."""

    def __init__(
        self,
        sandy_service: SandyService,
        pool_size: int = 2,
        max_age_seconds: int = 3600,
        max_requests: int = 10,
        maintenance_interval: int = 60,
        refill_on_acquire: bool = True,
    ) -> None:
        self.sandy = sandy_service
        self.pool_size = max(pool_size, 0)
        self.max_age_seconds = max_age_seconds
        self.max_requests = max_requests
        self.maintenance_interval = maintenance_interval
        self.refill_on_acquire = refill_on_acquire
        self._pool: list[WarmSandbox] = []
        self._lock = asyncio.Lock()
        self._fill_lock = asyncio.Lock()
        self._maintenance_task: asyncio.Task[None] | None = None

    @property
    def size(self) -> int:
        return len(self._pool)

    async def start(self) -> None:
        """Initialize pool with warm sandboxes."""
        if not self.sandy.is_available:
            logger.info("warm_pool_disabled", reason="sandy_unavailable")
            return
        if self.pool_size <= 0:
            logger.info("warm_pool_disabled", reason="pool_size_zero")
            return
        await self._fill_pool()
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())

    async def stop(self) -> None:
        """Stop maintenance and terminate pooled sandboxes."""
        if self._maintenance_task:
            self._maintenance_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._maintenance_task
            self._maintenance_task = None
        await self._drain_pool()

    async def acquire(self) -> WarmSandbox | None:
        """Get a warm sandbox from the pool."""
        if not self.sandy.is_available:
            return None
        while True:
            async with self._lock:
                sandbox = self._pool.pop(0) if self._pool else None
            if sandbox is None:
                return await self._create_warm_sandbox()
            if self._is_expired(sandbox):
                await sandbox.terminate()
                continue
            if self.refill_on_acquire:
                asyncio.create_task(self._fill_pool())
            return sandbox

    async def release(self, sandbox: WarmSandbox, reusable: bool = True) -> None:
        """Return sandbox to pool or terminate."""
        if not reusable or not sandbox.is_reusable() or self._is_expired(sandbox):
            if sandbox.termination_scheduled:
                return
            await sandbox.terminate()
            return

        await sandbox.reset()
        async with self._lock:
            if len(self._pool) < self.pool_size:
                self._pool.append(sandbox)
                return

        await sandbox.terminate()

    async def _fill_pool(self) -> None:
        """Fill pool to target size."""
        async with self._fill_lock:
            while True:
                async with self._lock:
                    missing = self.pool_size - len(self._pool)
                if missing <= 0:
                    return
                sandbox = await self._create_warm_sandbox()
                if sandbox is None:
                    return
                async with self._lock:
                    if len(self._pool) < self.pool_size:
                        self._pool.append(sandbox)
                    else:
                        await sandbox.terminate()
                        return

    async def _maintenance_loop(self) -> None:
        """Periodic health check and refresh."""
        while True:
            await asyncio.sleep(self.maintenance_interval)
            await self._health_check()
            await self._expire_old_sandboxes()
            await self._fill_pool()

    async def _health_check(self) -> None:
        """Check pool health and remove unhealthy sandboxes."""
        async with self._lock:
            sandboxes = list(self._pool)
        for sandbox in sandboxes:
            healthy = await self.sandy.check_sandbox(sandbox.sandbox_id)
            if healthy:
                continue
            await self._remove_sandbox(sandbox)

    async def _expire_old_sandboxes(self) -> None:
        """Expire old sandboxes based on age or request count."""
        async with self._lock:
            sandboxes = list(self._pool)
        for sandbox in sandboxes:
            if self._is_expired(sandbox):
                await self._remove_sandbox(sandbox)

    async def _remove_sandbox(self, sandbox: WarmSandbox) -> None:
        async with self._lock:
            if sandbox in self._pool:
                self._pool.remove(sandbox)
        if sandbox.termination_scheduled:
            return
        await sandbox.terminate()

    async def _drain_pool(self) -> None:
        async with self._lock:
            sandboxes = list(self._pool)
            self._pool.clear()
        for sandbox in sandboxes:
            if sandbox.termination_scheduled:
                continue
            await sandbox.terminate()

    async def _create_warm_sandbox(self) -> WarmSandbox | None:
        sandbox_info = await self.sandy.prepare_warm_sandbox()
        if not sandbox_info:
            return None
        sandbox_id, public_url = sandbox_info
        return WarmSandbox(
            sandbox_id=sandbox_id,
            public_url=public_url,
            created_at=_utcnow(),
            sandy_service=self.sandy,
        )

    def _is_expired(self, sandbox: WarmSandbox) -> bool:
        if self.max_age_seconds > 0:
            age_seconds = (_utcnow() - sandbox.created_at).total_seconds()
            if age_seconds > self.max_age_seconds:
                return True
        if self.max_requests > 0 and sandbox.request_count >= self.max_requests:
            return True
        return False

    def status(self) -> dict[str, int | bool]:
        return {
            "enabled": self.sandy.is_available and self.pool_size > 0,
            "size": len(self._pool),
            "target": self.pool_size,
        }
