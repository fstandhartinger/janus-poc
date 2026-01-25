"""Debug event models for baseline telemetry."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class DebugEventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    COMPLEXITY_CHECK_START = "complexity_check_start"
    COMPLEXITY_CHECK_KEYWORD = "complexity_check_keyword"
    COMPLEXITY_CHECK_LLM = "complexity_check_llm"
    COMPLEXITY_CHECK_COMPLETE = "complexity_check_complete"
    FAST_PATH_START = "fast_path_start"
    FAST_PATH_STREAM = "fast_path_stream"
    AGENT_PATH_START = "agent_path_start"
    SANDBOX_INIT = "sandbox_init"
    AGENT_THINKING = "agent_thinking"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    ARTIFACT_GENERATED = "artifact_generated"
    RESPONSE_CHUNK = "response_chunk"
    RESPONSE_COMPLETE = "response_complete"
    ERROR = "error"


class DebugEvent(BaseModel):
    request_id: str
    timestamp: str
    type: DebugEventType
    step: str
    message: str
    data: dict[str, Any] | None = None
