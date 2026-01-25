"""Deep research client for Janus agents."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import AsyncIterator, Callable

import httpx

_DEFAULT_BASE_URL = "https://search.chutes.ai"
_DEFAULT_TIMEOUT = 1200


@dataclass
class ResearchProgress:
    """Progress update during research."""

    stage: str
    status: str
    detail: str
    percent: float


@dataclass
class ResearchSource:
    """A source used in research."""

    title: str
    url: str
    snippet: str


@dataclass
class ResearchResult:
    """Complete research result."""

    report: str
    sources: list[ResearchSource]
    query: str
    mode: str
    duration_seconds: float


class DeepResearchClient:
    """Client for chutes-search deep research API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("CHUTES_SEARCH_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("CHUTES_API_KEY")
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _payload(
        query: str,
        mode: str,
        optimization: str,
        include_deep_research: bool,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "messages": [{"role": "user", "content": query}],
            "focusMode": "webSearch",
        }
        if include_deep_research:
            payload["deepResearchMode"] = mode
            payload["optimizationMode"] = optimization
        return payload

    async def _iter_events(self, payload: dict[str, object]) -> AsyncIterator[dict]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    yield data

    @staticmethod
    def _flatten_sources(raw: object) -> list[dict[str, object]]:
        if isinstance(raw, list):
            flattened: list[dict[str, object]] = []
            for entry in raw:
                if isinstance(entry, list):
                    flattened.extend(
                        [item for item in entry if isinstance(item, dict)]
                    )
                elif isinstance(entry, dict):
                    flattened.append(entry)
            return flattened
        if isinstance(raw, dict):
            return [raw]
        return []

    @staticmethod
    def _source_key(source: ResearchSource) -> str:
        return source.url or source.title

    def _merge_sources(
        self,
        sources: list[ResearchSource],
        raw: object,
        seen: set[str],
    ) -> None:
        for entry in self._flatten_sources(raw):
            metadata = entry.get("metadata") if isinstance(entry, dict) else None
            metadata = metadata if isinstance(metadata, dict) else {}
            title = str(metadata.get("title") or entry.get("title") or "")
            url = str(metadata.get("url") or entry.get("url") or "")
            snippet = entry.get("pageContent") or entry.get("snippet") or ""
            snippet_text = str(snippet)[:200]
            source = ResearchSource(title=title, url=url, snippet=snippet_text)
            key = self._source_key(source)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            sources.append(source)

    async def _stream_events_with_fallback(
        self,
        query: str,
        mode: str,
        optimization: str,
    ) -> AsyncIterator[dict]:
        payload = self._payload(query, mode, optimization, include_deep_research=True)
        fallback_payload = self._payload(
            query, mode, optimization, include_deep_research=False
        )
        sent_any = False
        try:
            async for event in self._iter_events(payload):
                sent_any = True
                yield event
            return
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            if sent_any:
                yield {"type": "error", "data": {"detail": str(exc)}}
                return
        except Exception as exc:  # pragma: no cover - defensive
            if sent_any:
                yield {"type": "error", "data": {"detail": str(exc)}}
                return

        try:
            async for event in self._iter_events(fallback_payload):
                yield event
        except Exception as exc:
            yield {"type": "error", "data": {"detail": str(exc)}}

    async def research(
        self,
        query: str,
        mode: str = "light",
        optimization: str = "balanced",
        on_progress: Callable[[ResearchProgress], None] | None = None,
    ) -> ResearchResult:
        """
        Perform deep research on a topic.

        Args:
            query: Research question or topic
            mode: "light" (faster, 10 sources) or "max" (thorough, 18 sources)
            optimization: "speed", "balanced", or "quality"
            on_progress: Optional callback for progress updates

        Returns:
            ResearchResult with report and sources
        """
        report_chunks: list[str] = []
        sources: list[ResearchSource] = []
        seen_sources: set[str] = set()
        error_detail: str | None = None
        start_time = time.monotonic()

        async for data in self._stream_events_with_fallback(query, mode, optimization):
            event_type = data.get("type") if isinstance(data, dict) else None
            if event_type == "progress":
                if on_progress:
                    payload = data.get("data") if isinstance(data, dict) else {}
                    payload = payload if isinstance(payload, dict) else {}
                    progress = ResearchProgress(
                        stage=str(payload.get("label") or ""),
                        status=str(payload.get("status") or ""),
                        detail=str(payload.get("detail") or ""),
                        percent=float(payload.get("percent") or 0),
                    )
                    on_progress(progress)
            elif event_type == "sources":
                raw_sources = data.get("data") if isinstance(data, dict) else None
                self._merge_sources(sources, raw_sources, seen_sources)
            elif event_type == "response":
                chunk = data.get("data") if isinstance(data, dict) else ""
                report_chunks.append(str(chunk or ""))
            elif event_type == "error":
                payload = data.get("data") if isinstance(data, dict) else {}
                payload = payload if isinstance(payload, dict) else {}
                error_detail = str(payload.get("detail") or "")

        duration = max(0.0, time.monotonic() - start_time)
        report = "".join(report_chunks)
        if error_detail:
            if report:
                report = f"{report}\n\nNote: {error_detail}"
            else:
                report = f"Deep research failed: {error_detail}"

        return ResearchResult(
            report=report,
            sources=sources,
            query=query,
            mode=mode,
            duration_seconds=duration,
        )

    async def research_stream(
        self,
        query: str,
        mode: str = "light",
        optimization: str = "balanced",
    ) -> AsyncIterator[str]:
        """
        Stream research progress and results.

        Yields formatted strings suitable for display.
        """

        def format_progress(progress: ResearchProgress) -> str:
            return f"- {progress.stage}: {progress.detail}"

        sources: list[ResearchSource] = []
        seen_sources: set[str] = set()
        report_started = False
        separator_sent = False

        async for data in self._stream_events_with_fallback(query, mode, optimization):
            event_type = data.get("type") if isinstance(data, dict) else None
            if event_type == "progress":
                payload = data.get("data") if isinstance(data, dict) else {}
                payload = payload if isinstance(payload, dict) else {}
                progress = ResearchProgress(
                    stage=str(payload.get("label") or ""),
                    status=str(payload.get("status") or ""),
                    detail=str(payload.get("detail") or ""),
                    percent=float(payload.get("percent") or 0),
                )
                yield format_progress(progress) + "\n"
            elif event_type == "sources":
                raw_sources = data.get("data") if isinstance(data, dict) else None
                self._merge_sources(sources, raw_sources, seen_sources)
            elif event_type == "response":
                if not separator_sent:
                    yield "\n---\n\n"
                    separator_sent = True
                report_started = True
                chunk = data.get("data") if isinstance(data, dict) else ""
                yield str(chunk or "")
            elif event_type == "error":
                payload = data.get("data") if isinstance(data, dict) else {}
                payload = payload if isinstance(payload, dict) else {}
                detail = str(payload.get("detail") or "")
                if detail:
                    yield f"\n\nNote: {detail}\n"

        if report_started and sources:
            yield "\n\n---\n\n## Sources\n\n"
            for index, source in enumerate(sources, 1):
                title = source.title or source.url or f"Source {index}"
                url = source.url or ""
                if url:
                    yield f"{index}. [{title}]({url})\n"
                else:
                    yield f"{index}. {title}\n"


async def deep_research(
    query: str,
    mode: str = "light",
    verbose: bool = True,
) -> str:
    """
    Perform deep research and return formatted report.

    Args:
        query: What to research
        mode: "light" or "max"
        verbose: Print progress updates

    Returns:
        Markdown-formatted research report with citations
    """
    client = DeepResearchClient()
    output: list[str] = []

    if verbose:
        print(f"Starting deep research ({mode} mode)...")
        print(f"Query: {query}\n")

    async for chunk in client.research_stream(query, mode):
        if verbose:
            print(chunk, end="", flush=True)
        output.append(chunk)

    return "".join(output)
