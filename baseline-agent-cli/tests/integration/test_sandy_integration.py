"""Tests for Sandy sandbox execution and artifact collection."""

from __future__ import annotations

import base64
import hashlib
import shlex
from dataclasses import dataclass, field

import httpx
import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.main import stream_response
from janus_baseline_agent_cli.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChunkChoice,
    Delta,
    Message,
    MessageRole,
)
from janus_baseline_agent_cli.services import ComplexityDetector, SandyService


@dataclass
class FakeResponse:
    payload: dict
    status_code: int = 200
    content: bytes = b""

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


@dataclass
class FakeAsyncClient:
    sandbox_id: str = "sbx_test"
    public_url: str = "http://sandbox.test"
    artifact_dir: str = "/workspace/artifacts"
    calls: list[dict] = field(default_factory=list)
    exec_commands: list[str] = field(default_factory=list)
    exec_timeouts: list[float | None] = field(default_factory=list)
    files: dict[str, bytes] = field(default_factory=dict)
    terminated: bool = False
    simulate_timeout: bool = False

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def _record_call(self, url: str, json: dict | None, timeout: float | None) -> None:
        self.calls.append({"url": url, "json": json, "timeout": timeout})

    def _handle_exec(self, command: str, timeout: float | None) -> FakeResponse:
        self.exec_commands.append(command)
        self.exec_timeouts.append(timeout)

        if "command -v" in command:
            if "aider" in command:
                return FakeResponse({"stdout": "/agent-pack/bin/aider\n", "stderr": "", "exit_code": 0})
            return FakeResponse({"stdout": "", "stderr": "", "exit_code": 1})

        if "find" in command and self.artifact_dir in command:
            paths = [path for path in self.files if path.startswith(self.artifact_dir)]
            return FakeResponse({"stdout": "\n".join(paths), "stderr": "", "exit_code": 0})

        if "bootstrap.sh" in command:
            return FakeResponse({"stdout": "Bootstrap ok", "stderr": "", "exit_code": 0})

        if command.startswith("echo "):
            text = command.split("echo", 1)[1].strip().strip("'\"")
            return FakeResponse({"stdout": f"{text}\n", "stderr": "", "exit_code": 0})

        if "pip install" in command:
            return FakeResponse({"stdout": "installed", "stderr": "", "exit_code": 0})

        if "aider" in command or "run_agent.py" in command:
            if self.simulate_timeout:
                raise httpx.ReadTimeout("timeout")
            parts = shlex.split(command)
            task = ""
            for index, part in enumerate(parts):
                if part.endswith("run_agent.py") or part == "aider":
                    if index + 1 < len(parts):
                        task = parts[index + 1]
                    break
            artifact_path = f"{self.artifact_dir}/agent_output.txt"
            self.files[artifact_path] = f"Artifact for {task}".encode("utf-8")
            return FakeResponse({"stdout": f"Completed: {task}", "stderr": "", "exit_code": 0})

        return FakeResponse({"stdout": "", "stderr": "", "exit_code": 0})

    async def post(self, url: str, json=None, headers=None, timeout=None) -> FakeResponse:
        self._record_call(url, json, timeout)

        if url.endswith("/api/sandboxes"):
            return FakeResponse({"sandbox_id": self.sandbox_id, "public_url": self.public_url})

        if "/files/write" in url:
            path = json.get("path") if json else None
            encoded = json.get("content") if json else None
            if path and encoded:
                self.files[path] = base64.b64decode(encoded)
            return FakeResponse({"ok": True})

        if "/exec" in url:
            command = json.get("command", "") if json else ""
            return self._handle_exec(command, timeout)

        if "/terminate" in url:
            self.terminated = True
            return FakeResponse({"ok": True})

        raise RuntimeError(f"Unhandled URL: {url}")

    async def get(self, url: str, params=None, headers=None, timeout=None) -> FakeResponse:
        if "/files/read" in url:
            path = params.get("path") if params else None
            if path and path in self.files:
                return FakeResponse({}, content=self.files[path])
            return FakeResponse({}, status_code=404)
        raise RuntimeError(f"Unhandled URL: {url}")


class StubLLMService:
    def __init__(self) -> None:
        self.called = False

    async def stream(self, request: ChatCompletionRequest):
        self.called = True
        yield ChatCompletionChunk(
            id="chatcmpl-test",
            model=request.model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )


class StubSandyService:
    is_available = True

    async def execute_complex(self, request: ChatCompletionRequest):
        raise AssertionError("Sandy path should not be used")


@pytest.mark.asyncio
async def test_fast_path_skips_sandy_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(always_use_agent=False)
    detector = ComplexityDetector(settings)
    llm = StubLLMService()
    sandy = StubSandyService()

    from janus_baseline_agent_cli import main as baseline_main

    monkeypatch.setattr(baseline_main, "settings", settings)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hello")],
        stream=True,
    )

    chunks = [chunk async for chunk in stream_response(request, detector, llm, sandy)]
    assert chunks
    assert llm.called is True


@pytest.mark.asyncio
async def test_complex_path_returns_artifacts() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(
        sandy_base_url="http://sandy.test",
        baseline_agent="aider",
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Write a script to process data")],
        stream=False,
    )

    response = await service.complete(request)

    assert any(call["url"].endswith("/api/sandboxes") for call in fake_client.calls)
    assert any("aider" in cmd for cmd in fake_client.exec_commands)

    message = response.choices[0].message
    artifacts = getattr(message, "artifacts", None)
    assert artifacts
    artifact = artifacts[0]

    assert artifact.display_name == "agent_output.txt"
    assert artifact.size_bytes > 0
    assert artifact.url

    if artifact.url.startswith("data:"):
        encoded = artifact.url.split("base64,", 1)[1]
        decoded = base64.b64decode(encoded)
        assert hashlib.sha256(decoded).hexdigest() == artifact.sha256
    else:
        assert artifact.url.endswith("/artifacts/agent_output.txt")

    assert "Artifacts available" in message.content


@pytest.mark.asyncio
async def test_sandy_env_passes_auth_token() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(
        sandy_base_url="http://sandy.test",
        sandy_api_key="fallback",
        baseline_agent="aider",
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Check sandbox env")],
        stream=False,
    )
    request._auth_token = "child-token"

    await service.complete(request)

    agent_command = next(
        cmd
        for cmd in fake_client.exec_commands
        if ("aider" in cmd or "run_agent.py" in cmd) and "command -v" not in cmd
    )
    assert "SANDY_API_KEY=child-token" in agent_command
    assert "SANDY_BASE_URL=" in agent_command
    assert "sandy.test" in agent_command


@pytest.mark.asyncio
async def test_streaming_includes_sandbox_events() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(
        sandy_base_url="http://sandy.test",
        baseline_agent="aider",
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Write code")],
        stream=True,
    )

    reasoning = []
    async for chunk in service.execute_complex(request):
        for choice in chunk.choices:
            if choice.delta.reasoning_content:
                reasoning.append(choice.delta.reasoning_content)

    reasoning_text = "".join(reasoning)
    assert "Creating Sandy sandbox" in reasoning_text
    assert "Terminating sandbox" in reasoning_text


@pytest.mark.asyncio
async def test_timeout_terminates_sandbox() -> None:
    fake_client = FakeAsyncClient(simulate_timeout=True)
    settings = Settings(
        sandy_base_url="http://sandy.test",
        sandy_timeout=1,
        baseline_agent="aider",
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Write code")],
        stream=True,
    )

    async for _ in service.execute_complex(request):
        pass

    assert fake_client.terminated is True
    assert any(timeout == 1 for timeout in fake_client.exec_timeouts)


@pytest.mark.asyncio
async def test_create_and_terminate_sandbox() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: fake_client)

    sandbox_id = await service.create_sandbox()
    assert sandbox_id.startswith("sbx_")

    await service.terminate(sandbox_id)
    assert fake_client.terminated is True


@pytest.mark.asyncio
async def test_execute_command() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: fake_client)

    sandbox_id = await service.create_sandbox()
    result = await service.exec(sandbox_id, "echo 'hello'")
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_write_and_read_file() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: fake_client)

    sandbox_id = await service.create_sandbox()
    await service.write_file(sandbox_id, "/workspace/test.txt", "content")
    content = await service.read_file(sandbox_id, "/workspace/test.txt")
    assert content == "content"


@pytest.mark.asyncio
async def test_install_package() -> None:
    fake_client = FakeAsyncClient()
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: fake_client)

    sandbox_id = await service.create_sandbox()
    result = await service.exec(sandbox_id, "pip install requests")
    assert result.exit_code == 0
