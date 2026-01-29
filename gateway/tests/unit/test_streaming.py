"""Unit tests for SSE helpers."""

from janus_gateway.services.streaming import (
    StreamChunk,
    create_done_marker,
    create_keep_alive,
    format_sse_chunk,
    parse_sse_line,
)


def test_format_content_chunk() -> None:
    chunk = StreamChunk(
        id="chatcmpl-123",
        object="chat.completion.chunk",
        created=1234567890,
        model="baseline",
        choices=[{"index": 0, "delta": {"content": "Hello"}}],
    )
    sse = format_sse_chunk(chunk)
    assert sse.startswith("data: ")
    assert "Hello" in sse
    assert sse.endswith("\n\n")


def test_format_reasoning_chunk() -> None:
    chunk = StreamChunk(
        id="chatcmpl-123",
        object="chat.completion.chunk",
        created=1234567890,
        model="baseline",
        choices=[{"index": 0, "delta": {"reasoning_content": "Thinking..."}}],
    )
    sse = format_sse_chunk(chunk)
    assert "reasoning_content" in sse


def test_done_marker() -> None:
    done = create_done_marker()
    assert done == "data: [DONE]\n\n"


def test_keep_alive_format() -> None:
    keep_alive = create_keep_alive()
    assert keep_alive == ": ping\n\n"


def test_parse_sse_line_data() -> None:
    line = 'data: {"id": "123"}'
    result = parse_sse_line(line)
    assert result["type"] == "data"
    assert result["content"]["id"] == "123"


def test_parse_sse_line_done() -> None:
    line = "data: [DONE]"
    result = parse_sse_line(line)
    assert result["type"] == "done"


def test_parse_sse_line_comment() -> None:
    line = ": ping"
    result = parse_sse_line(line)
    assert result["type"] == "comment"


def test_chunk_with_finish_reason() -> None:
    chunk = StreamChunk(
        id="chatcmpl-123",
        object="chat.completion.chunk",
        created=1234567890,
        model="baseline",
        choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
    )
    assert chunk.choices[0]["finish_reason"] == "stop"


def test_chunk_with_usage() -> None:
    chunk = StreamChunk(
        id="chatcmpl-123",
        object="chat.completion.chunk",
        created=1234567890,
        model="baseline",
        choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    )
    assert chunk.usage is not None
    assert chunk.usage["total_tokens"] == 30
