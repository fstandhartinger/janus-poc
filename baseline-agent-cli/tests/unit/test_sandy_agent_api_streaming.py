"""Unit tests for Sandy agent/run streaming handling."""

from __future__ import annotations

import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import ChatCompletionRequest, Message, MessageRole
from janus_baseline_agent_cli.services.sandy import SandyService


class DummyClient:
    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


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

    async def fake_run_agent(_client, _sandbox_id, _agent, _model, _prompt, max_duration=600):
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
    assert calls[:2] == ["upload", "bootstrap"]
    assert "run" in calls
