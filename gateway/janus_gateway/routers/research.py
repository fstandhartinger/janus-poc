"""Deep research proxy endpoint."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from typing import AsyncGenerator, Iterable, Literal

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


class FirecrawlError(Exception):
    """Firecrawl error when search fallback fails."""


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    snippet: str


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


def _progress_event(label: str, status: str, detail: str, percent: float) -> str:
    payload = {
        "type": "progress",
        "data": {
            "label": label,
            "status": status,
            "detail": detail,
            "percent": percent,
        },
    }
    return f"data: {json.dumps(payload)}\n\n"


def _sources_event(sources: Iterable[ResearchSource]) -> str:
    payload = {
        "type": "sources",
        "data": [
            {"title": source.title, "url": source.url, "snippet": source.snippet}
            for source in sources
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


def _response_event(text: str) -> str:
    payload = {"type": "response", "data": text}
    return f"data: {json.dumps(payload)}\n\n"


def _format_source_label(source: ResearchSource, index: int) -> str:
    if source.title:
        return source.title
    if source.url:
        return source.url
    return f"Source {index}"


def _build_report(query: str, sources: list[ResearchSource]) -> str:
    if not sources:
        return f"No sources found for: {query}"
    lines = ["## Research Summary", ""]
    for index, source in enumerate(sources, 1):
        label = _format_source_label(source, index)
        snippet = source.snippet.strip() if source.snippet else ""
        if snippet:
            lines.append(f"- {label}: {snippet} [{index}]")
        else:
            lines.append(f"- {label} [{index}]")
    return "\n".join(lines)


async def _firecrawl_search(
    client: httpx.AsyncClient,
    query: str,
    limit: int,
    api_key: str | None,
    base_url: str,
) -> list[ResearchSource]:
    if not api_key:
        raise FirecrawlError("Search API key not configured.")

    url = f"{base_url.rstrip('/')}/search"
    response = await client.post(
        url,
        json={"query": query, "limit": limit},
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise FirecrawlError("Search response malformed.")
    if not payload.get("success", False):
        raise FirecrawlError(str(payload.get("error", "Search failed.")))

    results = payload.get("data", [])
    if not isinstance(results, list):
        raise FirecrawlError("Search results malformed.")

    sources: list[ResearchSource] = []
    seen: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "")
        url_value = str(item.get("url") or item.get("link") or "")
        snippet = str(item.get("description") or item.get("snippet") or "")
        key = url_value or title
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        sources.append(ResearchSource(title=title, url=url_value, snippet=snippet))

    return sources


async def _stream_firecrawl_research(
    request: ResearchRequest,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    mode = request.mode
    limit = 10 if mode == "max" else 5
    yield _progress_event("Finding Sources", "running", "Searching the web", 10)

    try:
        async with httpx.AsyncClient(timeout=settings.firecrawl_timeout) as client:
            sources = await _firecrawl_search(
                client,
                request.query,
                limit,
                settings.firecrawl_api_key,
                settings.firecrawl_base_url,
            )
    except FirecrawlError as exc:
        yield _error_event(str(exc))
        return
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        yield _error_event(f"Search request failed: {exc}")
        return

    if not sources:
        yield _error_event("No sources found for this query.")
        return

    yield _progress_event(
        "Finding Sources",
        "complete",
        f"Found {len(sources)} sources",
        25,
    )
    yield _progress_event("Preparing Sandbox", "complete", "Using lightweight crawler", 30)
    yield _progress_event("Installing Browser", "complete", "Not required", 35)
    yield _progress_event("Launching Browser", "complete", "Not required", 40)
    yield _progress_event("Crawling Pages", "running", "Collecting snippets", 55)
    yield _progress_event(
        "Crawling Pages",
        "complete",
        f"Processed {len(sources)} sources",
        70,
    )
    yield _progress_event("Synthesizing Notes", "running", "Summarizing findings", 80)

    report = _build_report(request.query, sources)

    yield _progress_event("Synthesizing Notes", "complete", "Summary ready", 90)
    yield _progress_event("Drafting Report", "running", "Drafting report", 95)
    yield _response_event(report)
    yield _progress_event("Drafting Report", "complete", "Report drafted", 98)
    yield _sources_event(sources)
    yield _progress_event("Cleaning Up", "complete", "Finished", 100)
    yield "data: [DONE]\n\n"


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
            return
        except Exception as exc:
            logger.warning("deep_research_fallback_failed", error=str(exc))

        try:
            async for chunk in _stream_firecrawl_research(request, settings):
                yield chunk
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("deep_research_secondary_fallback_failed", error=str(exc))
            yield _error_event(
                "Deep research is temporarily unavailable. Please try again later."
            )

    return StreamingResponse(
        stream_research(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
