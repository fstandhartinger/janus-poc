"""Debug event streaming support for baseline telemetry."""

from __future__ import annotations

import asyncio
import structlog
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncGenerator

from janus_baseline_langchain.models.debug import DebugEvent, DebugEventType

logger = structlog.get_logger()


class DebugEventQueue:
    """In-memory queue for debug events per request."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[DebugEvent]] = defaultdict(asyncio.Queue)

    async def emit(self, request_id: str, event: DebugEvent) -> None:
        """Emit a debug event to the queue for a specific request."""
        await self._queues[request_id].put(event)

    async def subscribe(self, request_id: str) -> AsyncGenerator[DebugEvent, None]:
        """Subscribe to debug events for a specific request."""
        queue = self._queues[request_id]
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
                yield event
        except asyncio.TimeoutError:
            return
        finally:
            self._queues.pop(request_id, None)


debug_queue = DebugEventQueue()


class DebugEmitter:
    """Emits structured debug events for request tracing."""

    def __init__(
        self,
        request_id: str | None,
        enabled: bool,
        correlation_id: str | None = None,
    ) -> None:
        self._request_id = request_id
        self._enabled = enabled
        self._correlation_id = correlation_id

    def __bool__(self) -> bool:
        return self.enabled

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._request_id)

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id

    async def emit(
        self,
        event_type: DebugEventType,
        step: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit a structured debug event."""
        if not self._enabled or not self._request_id:
            return

        event = DebugEvent(
            request_id=self._request_id,
            timestamp=datetime.utcnow().isoformat(),
            type=event_type,
            step=step,
            message=message,
            data=data,
            correlation_id=self._correlation_id,
        )

        # Also log to structlog for aggregation
        logger.debug(
            event_type.value,
            debug_request_id=self._request_id,
            step=step,
            message=message,
            **(data or {}),
        )

        await debug_queue.emit(self._request_id, event)
