"""Request logging middleware with structured context and correlation IDs."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable, Mapping

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# Context variable for correlation ID - accessible from any async context
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Header names for correlation ID propagation
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-Id"


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_var.get() or ""


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get() or ""


def get_or_create_correlation_id(headers: dict[str, str] | None = None) -> str:
    """Get correlation ID from headers or create new one."""
    if headers:
        correlation_id = headers.get(CORRELATION_ID_HEADER) or headers.get(
            CORRELATION_ID_HEADER.lower()
        )
        if correlation_id:
            correlation_id_var.set(correlation_id)
            return correlation_id

    # Generate new correlation ID if not provided
    correlation_id = f"corr-{uuid.uuid4().hex[:16]}"
    correlation_id_var.set(correlation_id)
    return correlation_id


def _generate_request_id(prefix: str) -> str:
    token = uuid.uuid4().hex
    if prefix == "chatcmpl":
        return f"chatcmpl-{token[:24]}"
    return f"req_{token[:12]}"


def _request_id_prefix_for_path(path: str | None) -> str:
    if not path:
        return "req"
    if path.startswith("/v1/chat/completions"):
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
            request_id_var.set(request_id)
            return request_id

    request_id = _generate_request_id(_request_id_prefix_for_path(path))
    request_id_var.set(request_id)
    return request_id


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log requests with timing and correlation IDs for end-to-end tracing."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Get or create correlation + request ID for tracing
        headers = dict(request.headers)
        correlation_id = get_or_create_correlation_id(headers)
        request_id = get_or_create_request_id(headers, request.url.path)
        start_time = time.time()

        # Bind context for structured logging
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        # Add to request state for handlers
        request.state.request_id = request_id

        try:
            # Log request received with preview of query params
            logger.info(
                "request_received",
                query_params=dict(request.query_params),
            )

            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            logger.info(
                "request_complete",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                success=200 <= response.status_code < 400,
            )

            # Add tracing headers to response
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            response.headers[REQUEST_ID_HEADER] = request_id
            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise

        finally:
            # Clear context vars after request completes
            structlog.contextvars.clear_contextvars()
            # Reset correlation ID context var
            correlation_id_var.set("")
            request_id_var.set("")
