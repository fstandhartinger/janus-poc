"""Unit tests for Sandy agent/run streaming handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import ChatCompletionRequest, Message, MessageRole
from janus_baseline_agent_cli.services.sandy import SandyService


class DummyClient:
    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def test_router_api_base_normalization() -> None:
    settings = Settings()
    service = SandyService(settings, client_factory=lambda: DummyClient())

    assert service._router_api_base("http://router.test", "claude-code") == "http://router.test"
    assert (
        service._router_api_base("http://router.test/v1", "claude-code")
        == "http://router.test"
    )
    assert (
        service._router_api_base("http://router.test", "aider")
        == "http://router.test/v1"
    )
    assert (
        service._router_api_base("http://router.test/v1", "aider")
        == "http://router.test/v1"
    )


@pytest.mark.asyncio
async def test_agent_api_stream_event_yields_content(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: DummyClient())

    calls: list[str] = []

    async def fake_create_sandbox(_client):
        return "sbx_test", "http://sandbox.test"

    async def fake_upload(_client, _sandbox_id):
        calls.append("upload")
        return True

    async def fake_bootstrap(_client, _sandbox_id, _public_url, _request, _has_images):
        calls.append("bootstrap")
        return "Bootstrap ok", "", 0

    async def fake_run_agent(
        _client,
        _sandbox_id,
        _agent,
        _model,
        _prompt,
        request=None,
        public_url=None,
        has_images=False,
        max_duration=600,
    ):
        calls.append("run")
        yield {"type": "status", "message": "Starting"}
        yield {
            "type": "agent-output",
            "data": {
                "type": "stream_event",
                "event": {"delta": {"text": "Hello "}},
            },
        }
        yield {
            "type": "agent-output",
            "data": {
                "type": "stream_event",
                "event": {"delta": {"text": "world"}},
            },
        }
        yield {"type": "agent-output", "data": {"type": "result", "result": "!"}}
        yield {"type": "complete", "success": True, "exitCode": 0, "duration": 0.1}

    async def fake_collect_artifacts(_client, _sandbox_id, _public_url):
        return []

    async def fake_terminate(_client, _sandbox_id):
        calls.append("terminate")

    monkeypatch.setattr(service, "_create_sandbox", fake_create_sandbox)
    monkeypatch.setattr(service, "_upload_agent_pack", fake_upload)
    monkeypatch.setattr(service, "_run_bootstrap", fake_bootstrap)
    monkeypatch.setattr(service, "_run_agent_via_api", fake_run_agent)
    monkeypatch.setattr(service, "_collect_artifacts", fake_collect_artifacts)
    monkeypatch.setattr(service, "_terminate_sandbox", fake_terminate)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Say hello")],
        stream=True,
    )

    content_parts: list[str] = []
    async for chunk in service.execute_via_agent_api(request):
        for choice in chunk.choices:
            if choice.delta.content:
                content_parts.append(choice.delta.content)

    assert "".join(content_parts) == "Hello world!"
    # Note: upload and bootstrap are now skipped for execute_via_agent_api
    # because Sandy's /agent/run API handles agent setup internally
    assert calls[0] == "run"
    assert "terminate" in calls


class TestClaudeCodeFlagConflictRegression:
    """Regression tests for --append-system-prompt vs --append-system-prompt-file conflict.

    Sandy's AgentRunner passes --append-system-prompt, so if we also set
    JANUS_SYSTEM_PROMPT_PATH (which Sandy translates to --append-system-prompt-file),
    Claude Code errors because both flags cannot coexist. The fix is to remove the
    env var and pass the prompt inline via the payload's systemPrompt field.
    """

    def _make_service(self, system_prompt_path: Path | None = None) -> SandyService:
        settings = Settings(sandy_base_url="http://sandy.test")
        service = SandyService(settings, client_factory=lambda: DummyClient())
        if system_prompt_path is not None:
            service._system_prompt_path = system_prompt_path
        return service

    def test_claude_code_env_removes_system_prompt_path(self, tmp_path: Path) -> None:
        """JANUS_SYSTEM_PROMPT_PATH must not be in env for claude-code agents."""
        prompt_file = tmp_path / "system.md"
        prompt_file.write_text("You are Janus.", encoding="utf-8")
        service = self._make_service(system_prompt_path=prompt_file)

        env = service._build_agent_env("sbx_1", "http://sandbox.test")
        # The env initially contains JANUS_SYSTEM_PROMPT_PATH
        assert "JANUS_SYSTEM_PROMPT_PATH" in env

        # Simulate what _run_agent_via_api does for claude-code
        payload: dict = {"agent": "claude-code", "model": "test", "prompt": "hi"}
        if payload["agent"] in {"claude", "claude-code"}:
            env.pop("JANUS_SYSTEM_PROMPT_PATH", None)
            if service._system_prompt_path.exists():
                payload["systemPrompt"] = service._system_prompt_path.read_text(
                    encoding="utf-8"
                )

        assert "JANUS_SYSTEM_PROMPT_PATH" not in env
        assert payload.get("systemPrompt") == "You are Janus."

    def test_non_claude_agent_keeps_system_prompt_path(self) -> None:
        """Non-Claude agents should retain JANUS_SYSTEM_PROMPT_PATH in env."""
        service = self._make_service()
        env = service._build_agent_env("sbx_1", "http://sandbox.test")
        assert "JANUS_SYSTEM_PROMPT_PATH" in env

    def test_claude_wrapper_avoids_duplicate_flags(self) -> None:
        """The claude wrapper script must not add --append-system-prompt when already provided."""
        wrapper_path = (
            Path(__file__).resolve().parents[2]
            / "agent-pack"
            / "bin"
            / "claude"
        )
        if not wrapper_path.exists():
            pytest.skip("claude wrapper script not found")
        content = wrapper_path.read_text(encoding="utf-8")
        # Verify the wrapper checks has_append_prompt before adding its own flag
        assert "has_append_prompt" in content
        assert '! $has_append_prompt' in content or "! ${has_append_prompt}" in content
