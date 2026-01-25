"""Tests for the FastAPI entrypoint."""

import pytest
from fastapi.testclient import TestClient

from janus_baseline_langchain.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the baseline competitor."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_router_metrics_endpoint(client: TestClient) -> None:
    """Test router metrics endpoint exists."""
    response = client.get("/v1/router/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data


def test_chat_completion_with_tools_infers_tool_call(client: TestClient) -> None:
    """Test chat completion with tool inference (no API call needed)."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline-langchain",
            "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
            "stream": False,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert "choices" in data
    # Should have inferred tool call
    choice = data["choices"][0]
    assert choice["message"]["tool_calls"] is not None
    assert choice["message"]["tool_calls"][0]["function"]["name"] == "get_weather"


def test_chat_completion_streaming_with_tool_call(client: TestClient) -> None:
    """Test streaming chat completion with tool inference (no API call)."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline-langchain",
            "messages": [{"role": "user", "content": "Get the weather in London"}],
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"}
                            }
                        },
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data:" in response.text
    assert "get_weather" in response.text


def test_chat_completion_calculator_tool(client: TestClient) -> None:
    """Test calculator tool inference."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "baseline-langchain",
            "messages": [{"role": "user", "content": "Calculate 2 + 2"}],
            "stream": False,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": "Calculate expression",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    choice = data["choices"][0]
    assert choice["message"]["tool_calls"] is not None
    assert choice["message"]["tool_calls"][0]["function"]["name"] == "calculator"
