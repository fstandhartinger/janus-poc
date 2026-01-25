"""Tests for LangChain baseline tools."""

import json

import httpx
import pytest
from tavily import TavilyClient

from janus_baseline_langchain.tools import (
    InvestigateMemoryTool,
    code_execution_tool,
    image_generation_tool,
    music_generation_tool,
    text_to_speech_tool,
    web_search_tool,
)


@pytest.mark.asyncio
async def test_image_generation_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_CHUTES_API_KEY", "test-key")

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"data": [{"url": "https://example.com/image.png"}]}

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    result = await image_generation_tool.ainvoke("a sunset over mountains")
    assert result.startswith("http") or result.startswith("data:")


@pytest.mark.asyncio
async def test_tts_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_CHUTES_API_KEY", "test-key")

    class DummyResponse:
        content = b"fake-audio"

        def raise_for_status(self) -> None:
            return None

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    result = await text_to_speech_tool.ainvoke({"text": "Hello", "voice": "am_michael"})
    assert result.startswith(":::audio")
    assert "data:audio/wav;base64," in result


@pytest.mark.asyncio
async def test_music_generation_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_CHUTES_API_KEY", "test-key")

    class DummyResponse:
        content = b"fake-music"

        def raise_for_status(self) -> None:
            return None

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    result = await music_generation_tool.ainvoke(
        {
            "style_prompt": "Lo-fi beats",
            "lyrics": None,
            "steps": 32,
        }
    )
    assert result.startswith("data:audio")


@pytest.mark.asyncio
async def test_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_TAVILY_API_KEY", "test-key")

    def fake_search(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 5,
        include_answer: bool = True,
    ) -> dict[str, object]:
        return {"answer": "AI news", "results": [{"title": "Latest AI"}]}

    monkeypatch.setattr(TavilyClient, "search", fake_search)

    result = await web_search_tool.ainvoke("latest news about AI")
    data = json.loads(result)
    assert data["answer"] == "AI news"


@pytest.mark.asyncio
async def test_code_execution_tool() -> None:
    result = await code_execution_tool.ainvoke("print(2 + 2)")
    assert "4" in result


@pytest.mark.asyncio
async def test_investigate_memory_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def json(self) -> dict:
            return self._payload

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse(
                {
                    "memories": [
                        {
                            "id": "mem_1",
                            "caption": "User likes pizza",
                            "created_at": "2025-01-01T00:00:00Z",
                            "full_text": "User mentioned loving pizza during onboarding.",
                        }
                    ]
                }
            )

    monkeypatch.setattr(
        "janus_baseline_langchain.tools.memory.httpx.AsyncClient",
        FakeClient,
    )

    tool = InvestigateMemoryTool(
        user_id="user-1",
        memory_service_url="https://memory.test",
    )
    result = await tool.ainvoke({"memory_ids": ["mem_1"], "query": "pizza"})
    assert "## Retrieved Memories" in result
    assert "[mem_1] User likes pizza" in result
