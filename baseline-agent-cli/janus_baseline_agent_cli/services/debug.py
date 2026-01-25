"""Debug event streaming support for baseline telemetry."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncGenerator

from janus_baseline_agent_cli.models.debug import DebugEvent, DebugEventType


class DebugEventQueue:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[DebugEvent]] = defaultdict(asyncio.Queue)

    async def emit(self, request_id: str, event: DebugEvent) -> None:
        await self._queues[request_id].put(event)

    async def subscribe(self, request_id: str) -> AsyncGenerator[DebugEvent, None]:
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
    def __init__(self, request_id: str | None, enabled: bool) -> None:
        self._request_id = request_id
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._request_id)

    async def emit(
        self,
        event_type: DebugEventType,
        step: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        if not self._enabled or not self._request_id:
            return
        event = DebugEvent(
            request_id=self._request_id,
            timestamp=datetime.utcnow().isoformat(),
            type=event_type,
            step=step,
            message=message,
            data=data,
        )
        await debug_queue.emit(self._request_id, event)
