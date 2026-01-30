"""Integration tests for long-running agent task handling."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

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
from janus_baseline_agent_cli.routing import RoutingDecision
from janus_baseline_agent_cli.services.sandy import SandyService


class StubComplexityDetector:
    async def analyze_async(self, messages, flags=None, metadata=None):
        return SimpleNamespace(
            is_complex=True,
            reason="test",
            keywords_matched=[],
            multimodal_detected=False,
            has_images=False,
            image_count=0,
            text_preview="",
            decision=RoutingDecision.AGENT_KIMI,
        )


class StubLLMService:
    async def stream(self, request: ChatCompletionRequest):
        yield ChatCompletionChunk(
            id="chatcmpl-test",
            model=request.model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )


class StubSandyService:
    is_available = True

    async def execute_via_agent_api(self, request, debug_emitter=None, baseline_agent_override=None):
        yield ChatCompletionChunk(
            id="chatcmpl-test",
            model=request.model,
            choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
        )
        await asyncio.sleep(1.1)
        yield ChatCompletionChunk(
            id="chatcmpl-test",
            model=request.model,
            choices=[ChunkChoice(delta=Delta(content="done"))],
        )


class DummyClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_keepalive_emits_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    from janus_baseline_agent_cli import main as baseline_main

    settings = Settings(always_use_agent=True, sse_keepalive_interval=1)
    monkeypatch.setattr(baseline_main, "settings", settings)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Long task")],
        stream=True,
    )

    payloads = []
    async for payload in stream_response(
        request,
        StubComplexityDetector(),
        StubLLMService(),
        StubSandyService(),
    ):
        payloads.append(payload)
        if "data: [DONE]" in payload:
            break

    reasoning_parts = []
    content_parts = []
    for payload in payloads:
        for line in payload.splitlines():
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                continue
            event = json.loads(data)
            delta = (event.get("choices") or [{}])[0].get("delta", {})
            if delta.get("reasoning_content"):
                reasoning_parts.append(delta["reasoning_content"])
            if delta.get("content"):
                content_parts.append(delta["content"])

    assert any("Working..." in part for part in reasoning_parts)
    assert any("done" in part for part in content_parts)


@pytest.mark.asyncio
async def test_retry_emits_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(sandy_base_url="http://sandy.test")
    service = SandyService(settings, client_factory=lambda: DummyClient())

    async def fake_create_sandbox(self, client):
        return "sbx-test", "http://sandbox.test"

    async def fake_upload_agent_pack(self, client, sandbox_id):
        return True

    async def fake_run_bootstrap(self, client, sandbox_id, public_url, request, has_images):
        return "", "", 0

    async def fake_collect_artifacts(self, client, sandbox_id, public_url):
        return []

    async def fake_terminate_sandbox(self, client, sandbox_id):
        return None

    attempts = {"count": 0}

    async def fake_run_agent_via_api(
        self,
        client,
        sandbox_id,
        agent,
        model,
        task,
        *,
        request,
        public_url,
        has_images,
        max_duration,
    ):
        attempts["count"] += 1
        if attempts["count"] == 1:
            yield {"type": "error", "error": "Agent execution timed out: read timeout"}
            return
        yield {"type": "output", "text": "Completed task"}
        yield {"type": "complete", "exitCode": 0, "success": True, "duration": 1.0}

    async def no_sleep(_):
        return None

    monkeypatch.setattr(SandyService, "_create_sandbox", fake_create_sandbox)
    monkeypatch.setattr(SandyService, "_upload_agent_pack", fake_upload_agent_pack)
    monkeypatch.setattr(SandyService, "_run_bootstrap", fake_run_bootstrap)
    monkeypatch.setattr(SandyService, "_collect_artifacts", fake_collect_artifacts)
    monkeypatch.setattr(SandyService, "_terminate_sandbox", fake_terminate_sandbox)
    monkeypatch.setattr(SandyService, "_run_agent_via_api", fake_run_agent_via_api)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Retry task")],
        stream=True,
    )

    reasoning_parts = []
    content_parts = []
    async for chunk in service.execute_via_agent_api(request):
        for choice in chunk.choices:
            if choice.delta.reasoning_content:
                reasoning_parts.append(choice.delta.reasoning_content)
            if choice.delta.content:
                content_parts.append(choice.delta.content)

    assert any("retrying" in part.lower() for part in reasoning_parts)
    assert any("Completed task" in part for part in content_parts)
