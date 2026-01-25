"""Tests for artifact streaming events."""

import json

import pytest

from janus_baseline_langchain.main import stream_agent_response
from janus_baseline_langchain.models import Artifact, ArtifactType
from janus_baseline_langchain.services import add_artifact, start_artifact_collection


class DummyChunk:
    def __init__(self, content: str) -> None:
        self.content = content


class DummyAgent:
    async def astream_events(self, *args, **kwargs):
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": DummyChunk("hello")},
        }


@pytest.mark.asyncio
async def test_stream_agent_response_includes_artifacts() -> None:
    start_artifact_collection()
    add_artifact(
        Artifact(
            id="artifact-1",
            type=ArtifactType.FILE,
            mime_type="text/plain",
            display_name="note.txt",
            size_bytes=4,
            url="/artifacts/note.txt",
        )
    )

    agent = DummyAgent()
    chunks = []
    async for payload in stream_agent_response(
        agent,
        request_id="req-1",
        model="test-model",
        user_input="hi",
        history=[],
        include_usage=False,
    ):
        chunks.append(payload)

    joined = "".join(chunks)
    assert "artifacts" in joined

    for line in joined.splitlines():
        if not line.startswith("data:") or line.strip() == "data: [DONE]":
            continue
        data = json.loads(line.replace("data: ", ""))
        delta = data["choices"][0]["delta"]
        if delta.get("janus", {}).get("event") == "artifacts":
            assert delta["janus"]["payload"]["artifacts"][0]["id"] == "artifact-1"
            return

    raise AssertionError("Artifact event not found in stream")
