"""Tests for LangChain baseline tools."""

import json
from pathlib import Path

import httpx
import pytest
from tavily import TavilyClient

from janus_baseline_langchain.services import (
    get_collected_artifacts,
    set_request_auth_token,
    start_artifact_collection,
)
from janus_baseline_langchain.tools import (
    InvestigateMemoryTool,
    audio_generation_tool,
    clone_repository_tool,
    code_execution_tool,
    create_directory_tool,
    deep_research_tool,
    file_read_tool,
    file_write_tool,
    image_generation_tool,
    list_repository_files_tool,
    music_generation_tool,
    read_repository_file_tool,
    text_to_speech_tool,
    video_generation_tool,
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


@pytest.mark.asyncio
async def test_deep_research_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "answer": "Research summary.",
                "sources": [
                    {"title": "Example Source", "url": "https://example.com"},
                ],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        "janus_baseline_langchain.tools.deep_research.httpx.AsyncClient",
        FakeClient,
    )

    result = await deep_research_tool.ainvoke({"query": "Explain Janus", "mode": "max"})
    assert "Research summary." in result
    assert "Sources" in result
    assert "https://example.com" in result


@pytest.mark.asyncio
async def test_video_generation_tool_adds_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"url": "https://example.com/video.mp4"}

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    set_request_auth_token("user-token")
    start_artifact_collection()

    result = await video_generation_tool.ainvoke("Test video prompt")
    artifacts = get_collected_artifacts()

    assert "Video generated" in result
    assert artifacts
    assert artifacts[0].url == "https://example.com/video.mp4"


@pytest.mark.asyncio
async def test_audio_generation_tool_adds_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        content = b"fake-audio"

        def raise_for_status(self) -> None:
            return None

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    set_request_auth_token("user-token")
    start_artifact_collection()

    result = await audio_generation_tool.ainvoke({"prompt": "Hello", "type": "speech"})
    artifacts = get_collected_artifacts()

    assert result.startswith("data:audio/wav;base64,")
    assert artifacts


@pytest.mark.asyncio
async def test_file_tools_create_artifacts(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    monkeypatch.setenv("BASELINE_LANGCHAIN_ARTIFACTS_DIR", str(artifacts_dir))

    start_artifact_collection()
    result = await file_write_tool.ainvoke(
        {"filename": "report.txt", "content": "hello", "mime_type": "text/plain"}
    )
    assert "report.txt" in result

    artifacts = get_collected_artifacts()
    assert artifacts
    artifact_path = artifacts_dir / "report.txt"
    assert artifact_path.exists()

    read_result = await file_read_tool.ainvoke({"filename": "report.txt"})
    assert "hello" in read_result


@pytest.mark.asyncio
async def test_create_directory_tool(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("janus_baseline_langchain.tools.files.tempfile.gettempdir", lambda: str(tmp_path))

    result = await create_directory_tool.ainvoke({"path": "workdir/subdir"})
    created_path = Path(result)

    assert created_path.exists()
    assert created_path.is_dir()
    assert str(created_path).startswith(str(tmp_path))


@pytest.mark.asyncio
async def test_git_tools_clone_list_read(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    def fake_mkdtemp(prefix: str) -> str:  # type: ignore[no-untyped-def]
        return str(repo_path)

    class DummyResult:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(*args, **kwargs) -> DummyResult:  # type: ignore[no-untyped-def]
        return DummyResult()

    monkeypatch.setattr("janus_baseline_langchain.tools.git_tools.tempfile.mkdtemp", fake_mkdtemp)
    monkeypatch.setattr("janus_baseline_langchain.tools.git_tools.subprocess.run", fake_run)

    clone_result = await clone_repository_tool.ainvoke(
        {"url": "https://github.com/example/repo", "branch": "main"}
    )
    assert clone_result == str(repo_path)

    (repo_path / "README.md").write_text("Hello")
    (repo_path / ".git").mkdir()
    (repo_path / ".git" / "config").write_text("ignored")
    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("print('hi')")

    list_result = await list_repository_files_tool.ainvoke(
        {"repo_path": str(repo_path), "pattern": "*"}
    )
    assert "README.md" in list_result
    assert ".git" not in list_result

    read_result = await read_repository_file_tool.ainvoke(
        {"file_path": str(repo_path / "src" / "main.py")}
    )
    assert "print('hi')" in read_result


@pytest.mark.asyncio
async def test_auth_token_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_headers: dict[str, str] = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"url": "https://example.com/image.png"}]}

    def fake_post(*args, **kwargs) -> DummyResponse:  # type: ignore[no-untyped-def]
        captured_headers.update(kwargs.get("headers", {}))
        return DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    set_request_auth_token("passthrough-token")

    result = await image_generation_tool.ainvoke("token test")
    assert result.startswith("http")
    assert captured_headers.get("Authorization") == "Bearer passthrough-token"
