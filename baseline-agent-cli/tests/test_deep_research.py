"""Tests for deep research client."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Iterable

import httpx
import pytest

BASELINE_ROOT = Path(__file__).resolve().parents[1]
DEEP_RESEARCH_PATH = BASELINE_ROOT / "agent-pack" / "lib" / "deep_research.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("deep_research", DEEP_RESEARCH_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("Failed to load deep_research module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStreamResponse:
    def __init__(self, lines: Iterable[str], status_code: int = 200) -> None:
        self._lines = list(lines)
        self.status_code = status_code

    async def __aenter__(self) -> "FakeStreamResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class TimeoutStreamResponse:
    async def __aenter__(self) -> "TimeoutStreamResponse":
        raise httpx.TimeoutException("timeout")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeAsyncClient:
    def __init__(self, stream_response: Any) -> None:
        self._stream_response = stream_response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def stream(self, method: str, url: str, json: dict | None = None, headers: dict | None = None):
        self.calls.append({"method": method, "url": url, "json": json})
        return self._stream_response


@pytest.mark.asyncio
async def test_deep_research_parses_progress_and_sources(monkeypatch) -> None:
    module = load_module()
    lines = [
        'data: {"type":"progress","data":{"label":"Finding Sources","status":"running","detail":"searching","percent":10}}',
        'data: {"type":"response","data":"Hello "}',
        'data: {"type":"response","data":"world"}',
        (
            'data: {"type":"sources","data":[[{"metadata":{"title":"Example","url":"http://example.com"},'
            '"pageContent":"Snippet content"}]]}'
        ),
    ]
    response = FakeStreamResponse(lines)

    def fake_client(*args, **kwargs):
        return FakeAsyncClient(response)

    monkeypatch.setattr(module.httpx, "AsyncClient", fake_client)

    progress_updates: list[Any] = []
    client = module.DeepResearchClient(base_url="http://test")
    result = await client.research("topic", on_progress=progress_updates.append)

    assert result.report == "Hello world"
    assert progress_updates
    assert result.sources
    assert result.sources[0].url == "http://example.com"


@pytest.mark.asyncio
async def test_deep_research_fallback_on_timeout(monkeypatch) -> None:
    module = load_module()
    lines = ['data: {"type":"response","data":"Fallback result"}']
    responses = [TimeoutStreamResponse(), FakeStreamResponse(lines)]

    def fake_client(*args, **kwargs):
        return FakeAsyncClient(responses.pop(0))

    monkeypatch.setattr(module.httpx, "AsyncClient", fake_client)

    client = module.DeepResearchClient(base_url="http://test")
    result = await client.research("topic")

    assert result.report == "Fallback result"
