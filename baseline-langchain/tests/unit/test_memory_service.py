"""Tests for the memory service client."""

import httpx
import pytest

from janus_baseline_langchain.services.memory import MemoryService


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


@pytest.mark.asyncio
async def test_memory_context_formatting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memory context should include formatted references and prompt."""

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse({"memories": [{"id": "mem_1", "caption": "Likes tea"}]})

    monkeypatch.setattr(
        "janus_baseline_langchain.services.memory.httpx.AsyncClient",
        FakeClient,
    )

    service = MemoryService(base_url="https://memory.test", timeout=1.0)
    context = await service.get_memory_context("user-1", "Hello")

    assert "______ Notice ______" in context
    assert "- [mem_1] Likes tea" in context
    assert context.endswith("Hello")


@pytest.mark.asyncio
async def test_memory_context_empty_when_no_memories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memory context should be empty when service returns no memories."""

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse({"memories": []})

    monkeypatch.setattr(
        "janus_baseline_langchain.services.memory.httpx.AsyncClient",
        FakeClient,
    )

    service = MemoryService(base_url="https://memory.test", timeout=1.0)
    context = await service.get_memory_context("user-1", "Hello")

    assert context == ""


@pytest.mark.asyncio
async def test_memory_fetch_failure_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Memory service failures should not raise errors."""

    class FailingClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs):
            raise httpx.RequestError("boom", request=None)

    monkeypatch.setattr(
        "janus_baseline_langchain.services.memory.httpx.AsyncClient",
        FailingClient,
    )

    service = MemoryService(base_url="https://memory.test", timeout=1.0)
    context = await service.get_memory_context("user-1", "Hello")

    assert context == ""


@pytest.mark.asyncio
async def test_memory_extraction_failure_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extraction failures should be handled without raising errors."""

    class FailingClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, *args, **kwargs):
            raise httpx.RequestError("boom", request=None)

    monkeypatch.setattr(
        "janus_baseline_langchain.services.memory.httpx.AsyncClient",
        FailingClient,
    )

    service = MemoryService(base_url="https://memory.test", timeout=1.0)
    await service.extract_memories("user-1", [{"role": "user", "content": "Hi"}])
