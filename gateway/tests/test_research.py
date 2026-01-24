"""Tests for deep research proxy."""

from __future__ import annotations

from typing import Any, Iterable

import httpx


class FakeStreamResponse:
    def __init__(self, lines: Iterable[str], status_code: int = 200) -> None:
        self._lines = list(lines)
        self.status_code = status_code

    async def __aenter__(self) -> "FakeStreamResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return b"error"


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
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers})
        return self._stream_response


def test_research_proxy_streams_response(client, monkeypatch) -> None:
    response = FakeStreamResponse([
        'data: {"type":"response","data":"Hello"}',
    ])
    clients: list[FakeAsyncClient] = []

    def fake_client(*args, **kwargs):
        client_instance = FakeAsyncClient(response)
        clients.append(client_instance)
        return client_instance

    monkeypatch.setattr("janus_gateway.routers.research.httpx.AsyncClient", fake_client)

    result = client.post("/api/research", json={"query": "Hello"})
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("text/event-stream")
    lines = [line for line in result.iter_lines() if line.startswith("data:")]
    assert any("response" in line for line in lines)
    assert clients[0].calls[0]["json"]["deepResearchMode"] == "light"


def test_research_proxy_fallback_on_timeout(client, monkeypatch) -> None:
    responses = [TimeoutStreamResponse(), FakeStreamResponse([
        'data: {"type":"response","data":"Fallback"}',
    ])]
    clients: list[FakeAsyncClient] = []

    def fake_client(*args, **kwargs):
        client_instance = FakeAsyncClient(responses.pop(0))
        clients.append(client_instance)
        return client_instance

    monkeypatch.setattr("janus_gateway.routers.research.httpx.AsyncClient", fake_client)

    result = client.post("/api/research", json={"query": "Hello"})
    assert result.status_code == 200
    lines = [line for line in result.iter_lines() if line.startswith("data:")]
    assert any("Fallback" in line for line in lines)
    assert "deepResearchMode" not in clients[1].calls[0]["json"]
