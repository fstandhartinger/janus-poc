"""Debug event models for baseline telemetry."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class DebugEventType(str, Enum):
    # Request lifecycle
    REQUEST_RECEIVED = "request_received"

    # Complexity analysis
    COMPLEXITY_CHECK_START = "complexity_check_start"
    COMPLEXITY_CHECK_KEYWORD = "complexity_check_keyword"
    COMPLEXITY_CHECK_LLM = "complexity_check_llm"
    COMPLEXITY_CHECK_COMPLETE = "complexity_check_complete"
    ROUTING_DECISION = "routing_decision"

    # Fast path
    FAST_PATH_START = "fast_path_start"
    FAST_PATH_LLM_CALL = "fast_path_llm_call"
    FAST_PATH_STREAM = "fast_path_stream"
    FAST_PATH_COMPLETE = "fast_path_complete"

    # Agent path
    AGENT_PATH_START = "agent_path_start"
    AGENT_SELECTION = "agent_selection"
    MODEL_SELECTION = "model_selection"

    # Sandy interaction
    SANDBOX_INIT = "sandbox_init"
    SANDY_SANDBOX_CREATE = "sandy_sandbox_create"
    SANDY_SANDBOX_CREATED = "sandy_sandbox_created"
    SANDY_AGENT_API_REQUEST = "sandy_agent_api_request"
    SANDY_AGENT_API_SSE_EVENT = "sandy_agent_api_sse_event"
    SANDY_AGENT_API_COMPLETE = "sandy_agent_api_complete"
    SANDY_AGENT_API_ERROR = "sandy_agent_api_error"
    SANDY_SANDBOX_TERMINATE = "sandy_sandbox_terminate"

    # Prompt details
    PROMPT_ORIGINAL = "prompt_original"
    PROMPT_ENHANCED = "prompt_enhanced"
    PROMPT_SYSTEM = "prompt_system"

    # Agent execution
    AGENT_THINKING = "agent_thinking"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    TOOL_CALL_COMPLETE = "tool_call_complete"

    # File/artifact operations
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    ARTIFACT_GENERATED = "artifact_generated"
    ARTIFACT_CREATED = "artifact_created"

    # Response
    RESPONSE_CHUNK = "response_chunk"
    RESPONSE_COMPLETE = "response_complete"

    # Errors
    ERROR = "error"


class DebugEvent(BaseModel):
    request_id: str
    timestamp: str
    type: DebugEventType
    step: str
    message: str
    data: dict[str, Any] | None = None
    correlation_id: str | None = None
