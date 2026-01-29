"""Request tracing middleware wrapper."""

from janus_gateway.middleware.logging import RequestLoggingMiddleware

RequestTracingMiddleware = RequestLoggingMiddleware

__all__ = ["RequestTracingMiddleware", "RequestLoggingMiddleware"]
