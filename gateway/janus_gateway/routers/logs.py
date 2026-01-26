"""Log aggregation endpoint for client-side logs."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/logs", tags=["logs"])
logger = structlog.get_logger()


class LogContext(BaseModel):
    """Context information for a log entry."""

    correlationId: str | None = None
    requestId: str | None = None
    component: str | None = None


class LogEntry(BaseModel):
    """A single log entry from the client."""

    timestamp: str
    level: str = Field(..., pattern=r"^(debug|info|warn|error)$")
    message: str
    context: LogContext | None = None
    data: dict[str, Any] | None = None


class LogBatch(BaseModel):
    """Batch of log entries from the client."""

    logs: list[LogEntry]


@router.post("/ingest")
async def ingest_logs(batch: LogBatch) -> dict[str, Any]:
    """
    Ingest client-side logs.

    This endpoint receives batched logs from the UI client and writes them
    to the server's structured logging system for aggregation and analysis.

    The logs are enriched with source="ui_client" to distinguish them from
    server-generated logs.
    """
    processed = 0

    for entry in batch.logs:
        # Map client log level to structlog level
        log_level = entry.level.lower()

        # Prepare log context
        log_kwargs: dict[str, Any] = {
            "source": "ui_client",
            "client_timestamp": entry.timestamp,
        }

        # Add context fields if present
        if entry.context:
            if entry.context.correlationId:
                log_kwargs["correlation_id"] = entry.context.correlationId
            if entry.context.requestId:
                log_kwargs["request_id"] = entry.context.requestId
            if entry.context.component:
                log_kwargs["component"] = entry.context.component

        # Add custom data fields
        if entry.data:
            log_kwargs.update(entry.data)

        # Emit log at appropriate level
        if log_level == "debug":
            logger.debug(entry.message, **log_kwargs)
        elif log_level == "info":
            logger.info(entry.message, **log_kwargs)
        elif log_level == "warn":
            logger.warning(entry.message, **log_kwargs)
        elif log_level == "error":
            logger.error(entry.message, **log_kwargs)

        processed += 1

    return {"processed": processed, "status": "ok"}
