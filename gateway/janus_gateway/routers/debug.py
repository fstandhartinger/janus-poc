"""Debug stream proxy endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncGenerator, Iterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from janus_gateway.config import Settings, get_settings
from janus_gateway.services import CompetitorRegistry, get_competitor_registry
from janus_gateway.services.debug_registry import DebugRequestRegistry, get_debug_registry

router = APIRouter(prefix="/api/debug", tags=["debug"])

BASELINE_ALIASES = {
    "agent-cli": "baseline-cli-agent",
    "langchain": "baseline-langchain",
}

LOG_FILES = {
    "gateway": Path("/tmp/janus-gateway.log"),
    "baseline": Path("/tmp/janus-baseline.log"),
    "sandy": Path("/tmp/sandy.log"),
}


def _iter_log_entries() -> Iterator[tuple[str, dict[str, Any] | str]]:
    for service_name, path in LOG_FILES.items():
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                trimmed = line.strip()
                if not trimmed:
                    continue
                try:
                    payload = json.loads(trimmed)
                except json.JSONDecodeError:
                    payload = trimmed
                yield service_name, payload


def _match_log_filters(
    payload: dict[str, Any] | str,
    request_id: str | None,
    service: str | None,
    level: str | None,
    service_name: str,
) -> bool:
    raw = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
    if request_id and request_id not in raw:
        return False
    if level:
        level_value = payload.get("level") if isinstance(payload, dict) else None
        if level_value != level and level not in raw:
            return False
    if service:
        service_value = payload.get("service") if isinstance(payload, dict) else None
        if service_value != service and service_name != service and service not in raw:
            return False
    return True


def _collect_logs(
    request_id: str | None,
    service: str | None,
    level: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for service_name, payload in _iter_log_entries():
        if not _match_log_filters(payload, request_id, service, level, service_name):
            continue
        if isinstance(payload, dict):
            entry = dict(payload)
            entry.setdefault("service", service_name)
        else:
            entry = {"message": payload, "service": service_name}
        results.append(entry)
        if len(results) >= limit:
            break
    return results


@router.get("/stream/{request_id}")
async def proxy_debug_stream(
    request_id: str,
    baseline: str | None = None,
    registry: CompetitorRegistry = Depends(get_competitor_registry),
    debug_registry: DebugRequestRegistry = Depends(get_debug_registry),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    default_competitor = registry.get_default()
    baseline_id = baseline or debug_registry.resolve(request_id) or (default_competitor.id if default_competitor else "")
    baseline_id = BASELINE_ALIASES.get(baseline_id, baseline_id)
    competitor = registry.get(baseline_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Baseline not found")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                async with client.stream(
                    "GET",
                    f"{competitor.url}/v1/debug/stream/{request_id}",
                    timeout=settings.request_timeout,
                ) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        detail = error_body.decode("utf-8", errors="replace")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=detail or "Debug stream unavailable",
                        )
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:") or line.startswith("event:") or line.startswith(":"):
                            yield f"{line}\n\n"
        finally:
            debug_registry.discard(request_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/logs")
async def search_logs(
    request_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
    level: str | None = Query(default=None),
    since: str = Query(default="1h"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    """
    Search logs across services.

    For local dev, this scans local log files when present.
    """
    logs = _collect_logs(request_id, service, level, limit)
    return {
        "logs": logs,
        "filters_applied": {
            "request_id": request_id,
            "service": service,
            "level": level,
            "since": since,
        },
    }


@router.get("/trace/{request_id}")
async def get_request_trace(request_id: str) -> dict[str, Any]:
    """Return a summarized trace for a request ID."""
    logs = _collect_logs(request_id, None, None, 200)
    trace: list[dict[str, Any]] = []
    for entry in logs:
        trace.append(
            {
                "timestamp": entry.get("timestamp"),
                "service": entry.get("service"),
                "event": entry.get("event") or entry.get("message"),
                "duration_ms": entry.get("duration_ms"),
            }
        )
    return {"request_id": request_id, "trace": trace}
