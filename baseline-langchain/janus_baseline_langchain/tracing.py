"""Request tracing helpers for the LangChain baseline service."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Mapping
import uuid

CORRELATION_ID_HEADER = "X-Correlation-Id"
REQUEST_ID_HEADER = "X-Request-Id"

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_var.get() or ""


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get() or ""


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def _generate_request_id(prefix: str) -> str:
    token = uuid.uuid4().hex
    if prefix == "chatcmpl":
        return f"chatcmpl-{token[:24]}"
    return f"req_{token[:12]}"


def _request_id_prefix_for_path(path: str | None) -> str:
    if path and path.startswith("/v1/chat/completions"):
        return "chatcmpl"
    return "req"


def get_or_create_request_id(
    headers: Mapping[str, str] | None = None,
    path: str | None = None,
) -> str:
    """Get request ID from headers or create new one."""
    if headers:
        request_id = (
            headers.get(REQUEST_ID_HEADER)
            or headers.get(REQUEST_ID_HEADER.lower())
            or headers.get(REQUEST_ID_HEADER.upper())
        )
        if request_id:
            set_request_id(request_id)
            return request_id

    request_id = _generate_request_id(_request_id_prefix_for_path(path))
    set_request_id(request_id)
    return request_id


def get_or_create_correlation_id(headers: Mapping[str, str] | None = None) -> str:
    """Get correlation ID from headers or create new one."""
    if headers:
        correlation_id = (
            headers.get(CORRELATION_ID_HEADER)
            or headers.get(CORRELATION_ID_HEADER.lower())
            or headers.get(CORRELATION_ID_HEADER.upper())
        )
        if correlation_id:
            set_correlation_id(correlation_id)
            return correlation_id

    correlation_id = f"corr-{uuid.uuid4().hex[:16]}"
    set_correlation_id(correlation_id)
    return correlation_id


def clear_trace_context() -> None:
    """Clear request tracing context."""
    correlation_id_var.set("")
    request_id_var.set("")
