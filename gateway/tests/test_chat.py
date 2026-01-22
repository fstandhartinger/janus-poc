"""Tests for chat completions endpoint."""

from fastapi.testclient import TestClient


def test_chat_completion_non_streaming(client: TestClient) -> None:
    """Test non-streaming chat completion."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert "id" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] is not None


def test_chat_completion_streaming(client: TestClient) -> None:
    """Test streaming chat completion."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": True,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    # Collect streamed chunks
    chunks = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if data_str != "[DONE]":
                chunks.append(data_str)

    # Should have received some chunks
    assert len(chunks) > 0


def test_chat_completion_with_multipart_content(client: TestClient) -> None:
    """Test chat completion with text content parts."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see?"}
                    ]
                }
            ],
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"


def test_chat_completion_validation_error(client: TestClient) -> None:
    """Test that invalid requests are rejected."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline",
            # Missing required 'messages' field
        },
    )
    assert response.status_code == 422  # Validation error
