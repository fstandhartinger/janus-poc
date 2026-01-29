"""SSE helpers for chat streaming."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StreamChunk(BaseModel):
    """Serializable streaming chunk payload."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, Any] | None = None


def format_sse_chunk(chunk: StreamChunk) -> str:
    """Format a streaming chunk as an SSE data line."""
    payload = json.dumps(chunk.model_dump())
    return f"data: {payload}\n\n"


def create_done_marker() -> str:
    """Return the [DONE] marker."""
    return "data: [DONE]\n\n"


def create_keep_alive() -> str:
    """Return a keep-alive comment."""
    return ": ping\n\n"


def parse_sse_line(line: str) -> dict[str, Any]:
    """Parse a single SSE line."""
    trimmed = line.strip()
    if not trimmed or trimmed.startswith(":"):
        return {"type": "comment"}

    if not trimmed.startswith("data:"):
        return {"type": "unknown", "content": trimmed}

    data = trimmed[5:].strip()
    if data == "[DONE]":
        return {"type": "done"}

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return {"type": "error", "content": data}

    return {"type": "data", "content": parsed}
