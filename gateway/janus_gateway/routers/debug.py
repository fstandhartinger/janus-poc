"""Debug stream proxy endpoints."""

from __future__ import annotations

from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from janus_gateway.config import Settings, get_settings
from janus_gateway.services import CompetitorRegistry, get_competitor_registry
from janus_gateway.services.debug_registry import DebugRequestRegistry, get_debug_registry

router = APIRouter(prefix="/api/debug", tags=["debug"])

BASELINE_ALIASES = {
    "agent-cli": "baseline-cli-agent",
    "langchain": "baseline-langchain",
}


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
