"""Unit tests for response formatting helpers."""

from janus_baseline_agent_cli.services.response_formatting import (
    format_completion,
    format_sse_chunk,
    format_tool_call,
)


def test_format_streaming_chunk() -> None:
    """Format SSE streaming chunk."""
    chunk = format_sse_chunk({"content": "Hello"})
    assert chunk.startswith("data: ")
    assert "Hello" in chunk


def test_format_completion_response() -> None:
    """Format complete response."""
    response = format_completion({"content": "Response text", "model": "test-model"})
    assert response["choices"][0]["message"]["content"] == "Response text"


def test_format_tool_call_response() -> None:
    """Format tool call in response."""
    tool_call = format_tool_call(
        name="web_search",
        arguments={"query": "test"},
        id="call_123",
    )
    assert tool_call["function"]["name"] == "web_search"
