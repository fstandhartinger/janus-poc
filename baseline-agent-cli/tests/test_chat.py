"""Tests for chat completions endpoint."""

from fastapi.testclient import TestClient


def test_chat_completion_streaming(client: TestClient) -> None:
    """Test streaming chat completion."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    # Should receive SSE data
    content = response.text
    assert "data:" in content


def test_chat_completion_validation_error(client: TestClient) -> None:
    """Test that invalid requests are rejected."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            # Missing required 'messages' field
        },
    )
    assert response.status_code == 422  # Validation error


def test_chat_completion_sandy_unavailable_for_complex_request(
    client: TestClient,
) -> None:
    """Return a clear message when Sandy is unavailable for complex requests."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "run tests and take a screenshot"}],
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    message = data["choices"][0]["message"]["content"]
    assert "Agent sandbox is currently unavailable" in message
