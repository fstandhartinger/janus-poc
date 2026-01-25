"""Tests for transcription proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
import pytest

from janus_gateway.config import get_settings


class DummyResponse:
    def __init__(
        self, status_code: int, json_data: Optional[Dict[str, Any]] = None, text: str = ""
    ) -> None:
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

    async def post(
        self,
        url: str,
        headers: Dict[str, str],
        files: Dict[str, Any],
        data: Dict[str, Any],
    ) -> DummyResponse:
        self.request = {"url": url, "headers": headers, "files": files, "data": data}
        return self.response

    async def options(self, url: str) -> DummyResponse:
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

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient", mock_client
    )

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
        data={"language": "en"},
    )
    assert result.status_code == 200
    assert result.json() == {"text": "hello", "language": "en", "duration": 1.2}


def test_transcribe_audio_missing_api_key(client, monkeypatch) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    get_settings.cache_clear()

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
    )
    assert result.status_code == 503
    detail = result.json()["detail"]
    assert detail["code"] == "TRANSCRIPTION_NOT_CONFIGURED"
    assert detail["recoverable"] is False
    assert "suggestion" in detail


def test_transcribe_audio_missing_audio(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"", "audio/webm")},
        data={"language": "en"},
    )
    assert result.status_code == 400
    detail = result.json()["detail"]
    assert detail["code"] == "MISSING_AUDIO"
    assert detail["recoverable"] is True


def test_transcribe_audio_upstream_error(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=500, text="bad")

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient", mock_client
    )

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
    )
    assert result.status_code == 500
    detail = result.json()["detail"]
    assert detail["code"] == "UPSTREAM_ERROR"
    assert "Transcription failed" in detail["error"]


def test_transcribe_audio_timeout(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    class TimeoutClient:
        async def __aenter__(self) -> "TimeoutClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url, headers, files, data) -> DummyResponse:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient",
        lambda *args, **kwargs: TimeoutClient(),
    )

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
    )
    assert result.status_code == 504
    detail = result.json()["detail"]
    assert detail["code"] == "TIMEOUT"
    assert detail["recoverable"] is True


def test_transcribe_audio_rate_limit(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=429, text="rate limited")

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient", mock_client
    )

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
    )
    assert result.status_code == 429
    detail = result.json()["detail"]
    assert detail["code"] == "RATE_LIMITED"
    assert detail["recoverable"] is True


def test_transcribe_audio_invalid_api_key(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=401, text="invalid api key")

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient", mock_client
    )

    result = client.post(
        "/api/transcribe",
        files={"file": ("recording.webm", b"foo", "audio/webm")},
    )
    assert result.status_code == 503
    detail = result.json()["detail"]
    assert detail["code"] == "INVALID_API_KEY"
    assert detail["recoverable"] is False


def test_transcribe_health_api_key_not_configured(client, monkeypatch) -> None:
    monkeypatch.delenv("CHUTES_API_KEY", raising=False)
    get_settings.cache_clear()

    result = client.get("/api/transcribe/health")
    assert result.status_code == 200
    data = result.json()
    assert data["available"] is False
    assert data["api_key_configured"] is False
    assert "CHUTES_API_KEY" in data["error"]


def test_transcribe_health_api_key_configured(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    response = DummyResponse(status_code=200)

    def mock_client(*args, **kwargs) -> MockAsyncClient:
        return MockAsyncClient(response)

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient", mock_client
    )

    result = client.get("/api/transcribe/health")
    assert result.status_code == 200
    data = result.json()
    assert data["available"] is True
    assert data["api_key_configured"] is True
    assert data["error"] is None


def test_transcribe_health_endpoint_unreachable(client, monkeypatch) -> None:
    monkeypatch.setenv("CHUTES_API_KEY", "test-key")
    get_settings.cache_clear()

    class ErrorClient:
        async def __aenter__(self) -> "ErrorClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def options(self, url: str) -> DummyResponse:
            raise httpx.RequestError("connection failed")

    monkeypatch.setattr(
        "janus_gateway.routers.transcription.httpx.AsyncClient",
        lambda *args, **kwargs: ErrorClient(),
    )

    result = client.get("/api/transcribe/health")
    assert result.status_code == 200
    data = result.json()
    assert data["available"] is False
    assert data["api_key_configured"] is True
    assert "unreachable" in data["error"].lower()
