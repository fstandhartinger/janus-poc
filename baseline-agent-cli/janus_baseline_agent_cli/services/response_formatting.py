"""Helpers for formatting OpenAI-compatible responses."""

from __future__ import annotations

import json
from typing import Any

from janus_baseline_agent_cli.models import (
    ChatCompletionResponse,
    Choice,
    FinishReason,
    Message,
    MessageRole,
)


def format_sse_chunk(payload: dict[str, Any]) -> str:
    """Format a server-sent event chunk."""
    return f"data: {json.dumps(payload)}\n\n"


def format_completion(payload: dict[str, Any]) -> dict[str, Any]:
    """Format a non-streaming completion response payload."""
    content = str(payload.get("content", ""))
    model = str(payload.get("model", "baseline"))
    response = ChatCompletionResponse(
        id=str(payload.get("id", "chatcmpl-baseline-format")),
        model=model,
        choices=[
            Choice(
                message=Message(role=MessageRole.ASSISTANT, content=content),
                finish_reason=FinishReason.STOP,
            )
        ],
    )
    return response.model_dump()


def format_tool_call(name: str, arguments: dict[str, Any], id: str) -> dict[str, Any]:
    """Format a tool call payload."""
    return {
        "id": id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }
