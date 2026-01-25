"""Logging helpers for baseline services."""

from __future__ import annotations

import functools
import inspect

import structlog

logger = structlog.get_logger()


def log_function_call(func):
    """Log function entry/exit for sync and async callables."""

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def _async_wrapper(*args, **kwargs):
            logger.debug(
                "function_started",
                function=func.__qualname__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                logger.error(
                    "function_failed",
                    function=func.__qualname__,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise
            logger.debug("function_completed", function=func.__qualname__)
            return result

        return _async_wrapper

    @functools.wraps(func)
    def _sync_wrapper(*args, **kwargs):
        logger.debug(
            "function_started",
            function=func.__qualname__,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            logger.error(
                "function_failed",
                function=func.__qualname__,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        logger.debug("function_completed", function=func.__qualname__)
        return result

    return _sync_wrapper
