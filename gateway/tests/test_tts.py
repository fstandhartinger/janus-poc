"""Tests for TTS proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from janus_gateway.config import get_settings


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        content: bytes = b"",
        text: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self.content = content
        self.text = text
        self.headers = headers or {}


class MockAsyncClient:
    def __init__(self, response: DummyResponse) -> None:
        self.response = response
        self.request: Optional[Dict[str, Any]] = None

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, headers: Dict[str, str], json: Dict[str, Any]) -> DummyResponse:
        self.request = {"url": url, "headers": headers, "json": json}
        return self.response


def test_tts_success(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=200, content=b"audio", headers={"content-type": "audio/wav"})

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr("janus_gateway.routers.tts.httpx.AsyncClient", mock_client)

    result = client.post("/api/tts", json={"text": "Hello", "voice": "af_sky", "speed": 1.0})
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("audio/")
    assert result.content == b"audio"


def test_tts_missing_api_key(client, monkeypatch) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    get_settings.cache_clear()

    result = client.post("/api/tts", json={"text": "Hello"})
    assert result.status_code == 503


def test_tts_upstream_error(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=500, text="bad")

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr("janus_gateway.routers.tts.httpx.AsyncClient", mock_client)

    result = client.post("/api/tts", json={"text": "Hello"})
    assert result.status_code == 500
    assert "TTS failed" in result.json()["detail"]


def test_tts_timeout(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    class TimeoutClient:
        async def __aenter__(self) -> "TimeoutClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url, headers, json) -> DummyResponse:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("janus_gateway.routers.tts.httpx.AsyncClient", lambda *args, **kwargs: TimeoutClient())

    result = client.post("/api/tts", json={"text": "Hello"})
    assert result.status_code == 504
