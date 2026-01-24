"""Tests for transcription proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from janus_gateway.config import get_settings


class DummyResponse:
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, text: str = "") -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._json_data


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


def test_transcribe_audio_success(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(
        status_code=200,
        json_data={"text": "hello", "language": "en", "duration": 1.2},
    )

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr("janus_gateway.routers.transcription.httpx.AsyncClient", mock_client)

    result = client.post("/api/transcribe", json={"audio_b64": "Zm9v", "language": "en"})
    assert result.status_code == 200
    assert result.json() == {"text": "hello", "language": "en", "duration": 1.2}


def test_transcribe_audio_missing_api_key(client, monkeypatch) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    get_settings.cache_clear()

    result = client.post("/api/transcribe", json={"audio_b64": "Zm9v"})
    assert result.status_code == 503


def test_transcribe_audio_upstream_error(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=500, text="bad")

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr("janus_gateway.routers.transcription.httpx.AsyncClient", mock_client)

    result = client.post("/api/transcribe", json={"audio_b64": "Zm9v"})
    assert result.status_code == 500
    assert "Transcription failed" in result.json()["detail"]


def test_transcribe_audio_timeout(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    class TimeoutClient:
        async def __aenter__(self) -> "TimeoutClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url, headers, json) -> DummyResponse:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("janus_gateway.routers.transcription.httpx.AsyncClient", lambda *args, **kwargs: TimeoutClient())

    result = client.post("/api/transcribe", json={"audio_b64": "Zm9v"})
    assert result.status_code == 504
