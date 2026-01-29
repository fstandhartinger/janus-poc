"""Request tracing middleware for the baseline agent service."""

from __future__ import annotations

import time
from typing import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from janus_baseline_agent_cli.tracing import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    clear_trace_context,
    get_or_create_correlation_id,
    get_or_create_request_id,
)

logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Log requests with timing plus correlation/request IDs."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        headers = dict(request.headers)
        correlation_id = get_or_create_correlation_id(headers)
        request_id = get_or_create_request_id(headers, request.url.path)
        start_time = time.time()

        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            logger.info("request_received")
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_complete",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                success=200 <= response.status_code < 400,
            )
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
            structlog.contextvars.clear_contextvars()
            clear_trace_context()
