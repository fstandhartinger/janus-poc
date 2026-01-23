"""Tests for the FastAPI entrypoint."""

from fastapi.testclient import TestClient

import janus_baseline_langchain.main as main


class DummyAgent:
    async def ainvoke(self, payload):
        return {"output": "Hello from stub"}

    async def astream_events(self, payload, version="v2"):
        class DummyChunk:
            def __init__(self, content: str) -> None:
                self.content = content

        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": DummyChunk("Hello")},
        }


def test_chat_completion_non_streaming(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(main, "create_agent", lambda settings: DummyAgent())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline-langchain",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hello from stub"


def test_chat_completion_streaming(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(main, "create_agent", lambda settings: DummyAgent())

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline-langchain",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data:" in response.text
