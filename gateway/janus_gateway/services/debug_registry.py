"""Track debug request routing for SSE proxying."""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class DebugRequestInfo:
    baseline_id: str
    created_at: float


class DebugRequestRegistry:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl_seconds = ttl_seconds
        self._requests: dict[str, DebugRequestInfo] = {}

    def register(self, request_id: str, baseline_id: str) -> None:
        self._requests[request_id] = DebugRequestInfo(
            baseline_id=baseline_id,
            created_at=time.time(),
        )

    def resolve(self, request_id: str) -> str | None:
        self._cleanup()
        info = self._requests.get(request_id)
        return info.baseline_id if info else None

    def discard(self, request_id: str) -> None:
        self._requests.pop(request_id, None)

    def _cleanup(self) -> None:
        now = time.time()
        expired = [
            key
            for key, info in self._requests.items()
            if now - info.created_at > self._ttl_seconds
        ]
        for key in expired:
            self._requests.pop(key, None)


@lru_cache
def get_debug_registry() -> DebugRequestRegistry:
    return DebugRequestRegistry()
