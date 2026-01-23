"""Tests for the streaming contract and keep-alive behavior."""

import asyncio
import json
import time
from typing import Sequence

import pytest
from fastapi.testclient import TestClient

from janus_gateway.config import Settings
from janus_gateway.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChunkChoice,
    Delta,
    FinishReason,
    Message,
    MessageRole,
)
from janus_gateway.routers.chat import stream_from_competitor


class StubStreamResponse:
    """Stubbed streaming response for SSE lines."""

    def __init__(
        self,
        lines: Sequence[str],
        delays: Sequence[float] | None = None,
        status_code: int = 200,
    ) -> None:
        self.status_code = status_code
        self._lines = list(lines)
        if delays is None:
            self._delays = [0.0] * len(self._lines)
        else:
            if len(delays) != len(self._lines):
                raise ValueError("delays must match lines length")
            self._delays = list(delays)

    async def aiter_lines(self):  # type: ignore[override]
        for line, delay in zip(self._lines, self._delays, strict=True):
            if delay:
                await asyncio.sleep(delay)
            yield line

    async def aread(self) -> bytes:
        return b""


class StubStreamContext:
    """Async context manager wrapper for the stub response."""

    def __init__(self, response: StubStreamResponse) -> None:
        self._response = response

    async def __aenter__(self) -> StubStreamResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class StubClient:
    """Stub client that returns a provided streaming response."""

    def __init__(self, response: StubStreamResponse) -> None:
        self._response = response

    def stream(self, *args, **kwargs) -> StubStreamContext:
        return StubStreamContext(self._response)


@pytest.mark.asyncio
async def test_long_running_stream_emits_keep_alives() -> None:
    """Verify long-running streams stay open and emit keep-alives."""
    stream_duration = 180
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hello")],
        stream=True,
    )
    initial_chunk = ChatCompletionChunk(
        id="chatcmpl-test",
        model="baseline",
        choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
    )
    lines = [
        f"data: {initial_chunk.model_dump_json()}",
        "data: [DONE]",
    ]
    delays = [0.0, stream_duration]
    response = StubStreamResponse(lines, delays)
    client = StubClient(response)
    settings = Settings(keep_alive_interval=1.0)

    start = time.monotonic()
    keep_alive_count = 0
    async for payload in stream_from_competitor(
        client, "http://example.test", request, "req-test", settings
    ):
        if payload.startswith(":"):
            keep_alive_count += 1
        if payload.strip().endswith("[DONE]"):
            break
    elapsed = time.monotonic() - start

    assert elapsed >= stream_duration
    assert keep_alive_count >= int(stream_duration // 2)


@pytest.mark.asyncio
async def test_stream_passes_reasoning_and_janus_events() -> None:
    """Ensure reasoning content and Janus events pass through streaming."""
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hello")],
        stream=True,
    )
    settings = Settings(keep_alive_interval=1.0)

    tool_chunk = ChatCompletionChunk(
        id="chatcmpl-test",
        model="baseline",
        choices=[
            ChunkChoice(
                delta=Delta(
                    reasoning_content="Using tool...",
                    janus={"event": "tool_start", "payload": {"tool": "search"}},
                )
            )
        ],
    )
    sandbox_chunk = ChatCompletionChunk(
        id="chatcmpl-test",
        model="baseline",
        choices=[
            ChunkChoice(
                delta=Delta(
                    reasoning_content="Starting sandbox...",
                    janus={"event": "sandbox_start", "payload": {"sandbox_id": "test"}},
                )
            )
        ],
    )

    lines = [
        f"data: {tool_chunk.model_dump_json()}",
        f"data: {sandbox_chunk.model_dump_json()}",
        "data: [DONE]",
    ]
    response = StubStreamResponse(lines)
    client = StubClient(response)

    events = set()
    reasoning_seen = False
    async for payload in stream_from_competitor(
        client, "http://example.test", request, "req-test", settings
    ):
        if not payload.startswith("data:"):
            continue
        data_str = payload[5:].strip()
        if data_str == "[DONE]":
            break
        data = json.loads(data_str)
        delta = data["choices"][0]["delta"]
        if delta.get("reasoning_content"):
            reasoning_seen = True
        if "janus" in delta:
            events.add(delta["janus"]["event"])

    assert reasoning_seen
    assert "tool_start" in events
    assert "sandbox_start" in events


def test_stream_includes_usage_and_done(client: TestClient) -> None:
    """Verify usage chunk appears when requested and stream ends with DONE."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": True,
            "stream_options": {"include_usage": True},
            "competitor_id": "missing",
        },
    )
    assert response.status_code == 200

    data_lines = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())

    assert data_lines
    assert data_lines[-1] == "[DONE]"
    assert any(
        "usage" in json.loads(line)
        for line in data_lines
        if line != "[DONE]"
    )
