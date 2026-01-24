"""Deep research proxy endpoint."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import AsyncGenerator, Literal

import httpx
import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from janus_gateway.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["research"])
logger = structlog.get_logger()


class ResearchRequest(BaseModel):
    query: str
    mode: Literal["light", "max"] = "light"
    optimization: Literal["speed", "balanced", "quality"] = "balanced"


class UpstreamError(Exception):
    """Upstream error from chutes-search."""

    def __init__(self, status_code: int, body: bytes) -> None:
        super().__init__(f"Upstream error {status_code}")
        self.status_code = status_code
        self.body = body


def _build_payload(request: ResearchRequest, include_deep_research: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "messages": [{"role": "user", "content": request.query}],
        "focusMode": "webSearch",
    }
    if include_deep_research:
        payload["deepResearchMode"] = request.mode
        payload["optimizationMode"] = request.optimization
    return payload


def _error_event(detail: str) -> str:
    payload = {"type": "error", "data": {"detail": detail}}
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_chutes_search(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, object],
    headers: dict[str, str],
    keep_alive_interval: float,
) -> AsyncGenerator[str, None]:
    async with client.stream("POST", url, json=payload, headers=headers) as response:
        if response.status_code != 200:
            body = await response.aread()
            raise UpstreamError(response.status_code, body)

        line_queue: asyncio.Queue[object] = asyncio.Queue()
        done_sentinel = object()

        async def read_lines() -> None:
            try:
                async for line in response.aiter_lines():
                    await line_queue.put(line)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await line_queue.put(exc)
            finally:
                await line_queue.put(done_sentinel)

        reader_task = asyncio.create_task(read_lines())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        line_queue.get(), timeout=keep_alive_interval
                    )
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue

                if item is done_sentinel:
                    break
                if isinstance(item, Exception):
                    raise item

                line = str(item)
                if line.startswith("data:") or line.startswith(":"):
                    yield f"{line}\n\n"
        finally:
            if not reader_task.done():
                reader_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await reader_task


@router.post("/research")
async def deep_research(
    request: ResearchRequest,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """
    Proxy deep research requests to chutes-search.

    Streams SSE events for progress and results.
    """
    chutes_url = settings.chutes_search_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if settings.chutes_api_key:
        headers["Authorization"] = f"Bearer {settings.chutes_api_key}"

    payload = _build_payload(request, include_deep_research=True)
    fallback_payload = _build_payload(request, include_deep_research=False)
    stream_timeout = settings.deep_research_timeout

    async def stream_research() -> AsyncGenerator[str, None]:
        sent_any = False
        try:
            async with httpx.AsyncClient(timeout=stream_timeout) as client:
                async for chunk in _stream_chutes_search(
                    client,
                    f"{chutes_url}/api/chat",
                    payload,
                    headers,
                    settings.keep_alive_interval,
                ):
                    sent_any = True
                    yield chunk
                return
        except UpstreamError as exc:
            logger.warning(
                "deep_research_upstream_error",
                status_code=exc.status_code,
                body=exc.body.decode("utf-8", errors="ignore"),
            )
            if sent_any:
                yield _error_event("Deep research failed upstream.")
                return
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning("deep_research_stream_error", error=str(exc))
            if sent_any:
                yield _error_event("Deep research timed out.")
                return
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("deep_research_stream_error", error=str(exc))
            if sent_any:
                yield _error_event("Deep research failed.")
                return

        try:
            async with httpx.AsyncClient(timeout=stream_timeout) as client:
                async for chunk in _stream_chutes_search(
                    client,
                    f"{chutes_url}/api/chat",
                    fallback_payload,
                    headers,
                    settings.keep_alive_interval,
                ):
                    yield chunk
        except Exception as exc:
            logger.warning("deep_research_fallback_failed", error=str(exc))
            yield _error_event("Deep research unavailable; fallback failed.")

    return StreamingResponse(
        stream_research(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
