"""Tests for enhanced agent pack and Sandy integration."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import ChatCompletionRequest, Message, MessageRole
from janus_baseline_agent_cli.services.sandy import SandyService

BASELINE_ROOT = Path(__file__).resolve().parents[1]
AGENT_PACK_ROOT = BASELINE_ROOT / "agent-pack"
RUN_AGENT_PATH = AGENT_PACK_ROOT / "run_agent.py"


class FakeResponse:
    """Minimal httpx-like response for testing."""

    def __init__(self, data: dict, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def json(self) -> dict:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


class FakeAsyncClient:
    """Fake Sandy client that records calls and simulates exec output."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.exec_commands: list[str] = []
        self.written_files: list[str] = []
        self.sandbox_id = "sbx_test"

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def _run_agent(self, task: str) -> tuple[str, str, int]:
        env = os.environ.copy()
        env["JANUS_DOCS_ROOT"] = str(AGENT_PACK_ROOT / "models")
        env["JANUS_AGENT_PACK"] = str(AGENT_PACK_ROOT)
        result = subprocess.run(
            [sys.executable, str(RUN_AGENT_PATH), task],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return result.stdout, result.stderr, result.returncode

    async def post(self, url: str, json=None, headers=None, timeout=None) -> FakeResponse:
        self.calls.append({"url": url, "json": json})

        if url.endswith("/api/sandboxes"):
            return FakeResponse({"sandbox_id": self.sandbox_id})

        if "/files/write" in url:
            path = json.get("path") if json else None
            if path:
                self.written_files.append(path)
            return FakeResponse({"ok": True})

        if "/exec" in url:
            command = json.get("command", "") if json else ""
            self.exec_commands.append(command)
            if "bootstrap.sh" in command:
                return FakeResponse(
                    {
                        "stdout": (
                            "Agent pack initialized. Reference docs available at /workspace/docs/"
                        ),
                        "stderr": "",
                        "exit_code": 0,
                    }
                )
            if "run_agent.py" in command:
                parts = shlex.split(command)
                task = ""
                for index, part in enumerate(parts):
                    if part.endswith("run_agent.py"):
                        if index + 1 < len(parts):
                            task = parts[index + 1]
                        break
                stdout, stderr, exit_code = self._run_agent(task)
                return FakeResponse(
                    {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}
                )
            return FakeResponse({"stdout": "", "stderr": "", "exit_code": 0})

        if "/terminate" in url:
            return FakeResponse({"ok": True})

        raise RuntimeError(f"Unhandled URL: {url}")


def test_agent_pack_files_exist() -> None:
    """Agent pack should include reference docs and bootstrap."""
    assert (AGENT_PACK_ROOT / "models" / "text-to-speech.md").exists()
    assert (AGENT_PACK_ROOT / "models" / "text-to-image.md").exists()
    assert (AGENT_PACK_ROOT / "models" / "text-to-video.md").exists()
    assert (AGENT_PACK_ROOT / "models" / "lip-sync.md").exists()
    assert (AGENT_PACK_ROOT / "models" / "llm.md").exists()
    assert (AGENT_PACK_ROOT / "models" / "vision.md").exists()
    assert (AGENT_PACK_ROOT / "bootstrap.sh").exists()
    assert (AGENT_PACK_ROOT / "prompts" / "system.md").exists()
    assert (AGENT_PACK_ROOT / "lib" / "sandy_client.py").exists()
    assert (AGENT_PACK_ROOT / "lib" / "webapp_host.py").exists()


def test_system_prompt_content() -> None:
    """System prompt should reference tools and documentation."""
    prompt_path = BASELINE_ROOT / "agent-pack" / "prompts" / "system.md"
    content = prompt_path.read_text(encoding="utf-8")
    assert "Research & Discovery" in content
    assert "Code Execution" in content
    assert "File Operations" in content
    assert "Network & APIs" in content
    assert "File URL Patterns" in content
    assert "Safety Guardrails" in content
    assert "Sandbox Management" in content
    assert "docs/models/text-to-image.md" in content
    assert "docs/models/text-to-speech.md" in content
    assert "docs/models/vision.md" in content


def test_bootstrap_script_content() -> None:
    """Bootstrap should copy docs into workspace."""
    content = (AGENT_PACK_ROOT / "bootstrap.sh").read_text(encoding="utf-8")
    assert "cp /agent-pack/models/*.md /workspace/docs/models/" in content


def test_settings_support_capability_flags() -> None:
    """Settings should support toggling agent capabilities."""
    settings = Settings(
        enable_web_search=False,
        enable_code_execution=False,
        enable_file_tools=False,
    )
    assert settings.enable_web_search is False
    assert settings.enable_code_execution is False
    assert settings.enable_file_tools is False


@pytest.mark.asyncio
async def test_agent_answers_image_question_with_docs() -> None:
    """Agent should answer image generation questions using local docs."""
    fake_client = FakeAsyncClient()
    settings = Settings(
        sandy_base_url="http://sandy.test",
        agent_pack_path=str(AGENT_PACK_ROOT),
        system_prompt_path=str(AGENT_PACK_ROOT / "prompts" / "system.md"),
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[
            Message(role=MessageRole.USER, content="How do I generate an image with Chutes?")
        ],
    )

    content_chunks: list[str] = []
    async for chunk in service.execute_complex(request):
        for choice in chunk.choices:
            if choice.delta.content:
                content_chunks.append(choice.delta.content)

    combined = "\n".join(content_chunks)
    assert "https://image.chutes.ai/generate" in combined
    assert "docs/models/text-to-image.md" in combined
    assert any("bootstrap.sh" in command for command in fake_client.exec_commands)
    assert "/agent-pack/models/text-to-image.md" in fake_client.written_files


@pytest.mark.asyncio
async def test_agent_writes_tts_code() -> None:
    """Agent should provide working code for TTS calls."""
    fake_client = FakeAsyncClient()
    settings = Settings(
        sandy_base_url="http://sandy.test",
        agent_pack_path=str(AGENT_PACK_ROOT),
        system_prompt_path=str(AGENT_PACK_ROOT / "prompts" / "system.md"),
    )
    service = SandyService(settings, client_factory=lambda: fake_client)

    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[
            Message(role=MessageRole.USER, content="Write code for Chutes text-to-speech")
        ],
    )

    content_chunks: list[str] = []
    async for chunk in service.execute_complex(request):
        for choice in chunk.choices:
            if choice.delta.content:
                content_chunks.append(choice.delta.content)

    combined = "\n".join(content_chunks)
    assert "https://chutes-kokoro.chutes.ai/speak" in combined
    assert "requests.post" in combined
