# Spec 104: Request IDs and End-to-End Tracing

## Status: NOT STARTED

## Context / Why

When something fails in Janus, debugging is painful because:
1. No request IDs to correlate logs across services
2. No way to trace a request from UI → Gateway → Baseline → Sandy → Agent
3. Logs are scattered across multiple services
4. No tooling to quickly find and analyze failed requests

We need proper observability to debug production issues efficiently.

## Goals

- Add unique request IDs that propagate through all services
- Structured logging with consistent format
- Easy log correlation and search
- Timing/latency visibility at each hop
- Error context preservation

## Architecture

```
┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────┐    ┌───────┐
│    UI    │───▶│ Gateway │───▶│ Baseline │───▶│ Sandy │───▶│ Agent │
└──────────┘    └─────────┘    └──────────┘    └───────┘    └───────┘
     │               │               │              │            │
     ▼               ▼               ▼              ▼            ▼
   x-request-id: abc123 (propagated through all hops)
   x-parent-span-id: (for nested spans)

   All logs include:
   - request_id
   - service
   - timestamp
   - level
   - message
   - duration_ms (where applicable)
   - error (if any)
```

## Functional Requirements

### FR-1: Request ID Generation and Propagation

```python
# shared/tracing.py (or in each service)

import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"

def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()

def set_request_id(request_id: str):
    """Set request ID in context."""
    request_id_var.set(request_id)

# FastAPI middleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get("x-request-id") or generate_request_id()
        set_request_id(request_id)

        # Add to request state for handlers
        request.state.request_id = request_id

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response headers
            response.headers["x-request-id"] = request_id

            # Log request completion
            logger.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise
```

### FR-2: Structured Logging Setup

```python
# shared/logging_config.py

import structlog
import logging
import sys

def configure_logging(service_name: str, log_level: str = "INFO"):
    """Configure structured logging for a service."""

    # Structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add service name to all logs
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # JSON output for production, pretty for dev
    if sys.stderr.isatty():
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Get logger with service context
    return structlog.get_logger().bind(service=service_name)

# Usage in each service
# gateway/janus_gateway/main.py
logger = configure_logging("gateway")

# baseline-agent-cli/main.py
logger = configure_logging("baseline-agent-cli")
```

### FR-3: Request ID Propagation in HTTP Calls

```python
# When gateway calls baseline, propagate request ID

async def forward_to_baseline(
    request: ChatCompletionRequest,
    baseline_url: str,
) -> AsyncIterator[str]:
    """Forward request to baseline with tracing."""
    request_id = get_request_id()

    headers = {
        "x-request-id": request_id,
        "x-upstream-service": "gateway",
    }

    logger.info(
        "forwarding_to_baseline",
        request_id=request_id,
        baseline_url=baseline_url,
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{baseline_url}/v1/chat/completions",
            json=request.model_dump(),
            headers=headers,
            timeout=600,
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

### FR-4: Sandy Request Tracing

```python
# When baseline calls Sandy, include request ID

async def execute_in_sandy(
    request: AgentRequest,
    sandy_url: str,
) -> AsyncIterator[str]:
    """Execute agent in Sandy with tracing."""
    request_id = get_request_id()

    # Include request ID in Sandy request
    sandy_request = {
        **request.model_dump(),
        "metadata": {
            "request_id": request_id,
            "source_service": "baseline-agent-cli",
        }
    }

    logger.info(
        "executing_in_sandy",
        request_id=request_id,
        sandy_url=sandy_url,
    )

    # ... execute and stream
```

### FR-5: UI Request ID Display

```typescript
// Show request ID in UI for debugging

interface MessageMetadata {
  requestId?: string;
  model?: string;
  duration?: number;
}

function MessageFooter({ metadata }: { metadata: MessageMetadata }) {
  const [showDebug, setShowDebug] = useState(false);

  return (
    <div className="text-xs text-white/30 mt-2">
      {metadata.model && <span>{metadata.model}</span>}
      {metadata.duration && <span> · {metadata.duration}ms</span>}

      {/* Debug toggle */}
      <button
        onClick={() => setShowDebug(!showDebug)}
        className="ml-2 hover:text-white/50"
      >
        {showDebug ? '▼' : '▶'} Debug
      </button>

      {showDebug && metadata.requestId && (
        <div className="mt-1 font-mono">
          Request ID: {metadata.requestId}
          <button
            onClick={() => navigator.clipboard.writeText(metadata.requestId!)}
            className="ml-2 hover:text-white/50"
          >
            📋
          </button>
        </div>
      )}
    </div>
  );
}
```

### FR-6: Log Aggregation Endpoint (Debug Mode)

```python
# gateway/janus_gateway/routers/debug.py

from fastapi import APIRouter, Query
from typing import Optional
import subprocess

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/logs")
async def search_logs(
    request_id: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    since: Optional[str] = Query("1h"),  # e.g., "1h", "30m", "1d"
    limit: int = Query(100),
):
    """
    Search logs across services.

    In production, this would query a log aggregation service.
    For local dev, it searches local log files.
    """
    # This is a simplified version - production would use
    # Elasticsearch, Loki, CloudWatch, etc.

    filters = []
    if request_id:
        filters.append(f'"request_id":"{request_id}"')
    if service:
        filters.append(f'"service":"{service}"')
    if level:
        filters.append(f'"level":"{level}"')

    # For local dev, grep through log files
    # For production, query your log backend

    return {
        "logs": [],  # Would contain actual log entries
        "filters_applied": {
            "request_id": request_id,
            "service": service,
            "level": level,
            "since": since,
        }
    }

@router.get("/trace/{request_id}")
async def get_request_trace(request_id: str):
    """
    Get full trace for a request ID showing all hops.
    """
    # Would aggregate logs across services for this request
    return {
        "request_id": request_id,
        "trace": [
            {
                "timestamp": "2026-01-25T12:00:00Z",
                "service": "gateway",
                "event": "request_received",
                "duration_ms": None,
            },
            {
                "timestamp": "2026-01-25T12:00:00.050Z",
                "service": "gateway",
                "event": "forwarding_to_baseline",
                "duration_ms": 50,
            },
            # ... more trace entries
        ]
    }
```

### FR-7: Error Context Preservation

```python
# Wrap errors with request context

class TracedError(Exception):
    """Exception with tracing context."""

    def __init__(self, message: str, cause: Exception = None):
        self.request_id = get_request_id()
        self.cause = cause
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(message)

    def to_dict(self):
        return {
            "error": str(self),
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None,
            "cause_type": type(self.cause).__name__ if self.cause else None,
        }

# Usage
try:
    result = await sandy_client.execute(request)
except httpx.TimeoutException as e:
    raise TracedError("Sandy execution timed out", cause=e)
```

### FR-8: Timing Instrumentation

```python
# Decorator for timing functions

import functools
import time

def timed(name: str = None):
    """Decorator to log function execution time."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            fn_name = name or func.__name__
            request_id = get_request_id()
            start = time.time()

            logger.debug(f"{fn_name}_started", request_id=request_id)

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                logger.info(
                    f"{fn_name}_completed",
                    request_id=request_id,
                    duration_ms=round(duration_ms, 2),
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(
                    f"{fn_name}_failed",
                    request_id=request_id,
                    duration_ms=round(duration_ms, 2),
                    error=str(e),
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar for sync functions
            pass

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# Usage
@timed("complexity_analysis")
async def analyze_complexity(messages: list[Message]) -> ComplexityAnalysis:
    # ...
    pass
```

## Log Format Specification

### Standard Log Fields

Every log entry must include:

```json
{
  "timestamp": "2026-01-25T12:00:00.123Z",
  "level": "info",
  "service": "gateway",
  "request_id": "req_abc123def456",
  "event": "request_completed",
  "message": "Human-readable message",

  // Optional fields
  "duration_ms": 150.5,
  "error": "Error message if applicable",
  "error_type": "TimeoutError",
  "path": "/v1/chat/completions",
  "method": "POST",
  "status_code": 200,

  // Context fields (vary by event)
  "model": "baseline-agent-cli",
  "is_complex": true,
  "sandy_sandbox_id": "sandbox_xyz",
}
```

### Key Events to Log

| Service | Event | When |
|---------|-------|------|
| Gateway | `request_received` | Request arrives |
| Gateway | `complexity_detected` | After complexity analysis |
| Gateway | `forwarding_to_baseline` | Before calling baseline |
| Gateway | `request_completed` | Response sent |
| Baseline | `request_received` | Request arrives |
| Baseline | `fast_path_selected` | Using direct LLM |
| Baseline | `agent_path_selected` | Using Sandy agent |
| Baseline | `sandy_execution_started` | Agent execution begins |
| Baseline | `sandy_execution_completed` | Agent execution ends |
| Baseline | `stream_chunk_sent` | Each SSE chunk (debug only) |
| Sandy | `sandbox_created` | New sandbox |
| Sandy | `agent_started` | Agent begins |
| Sandy | `agent_completed` | Agent finishes |

## CLI Tool for Log Analysis

```bash
# scripts/log-search.sh

#!/bin/bash
# Search logs by request ID or other criteria

REQUEST_ID=$1

if [ -z "$REQUEST_ID" ]; then
    echo "Usage: ./log-search.sh <request_id>"
    exit 1
fi

# For local dev, search through service logs
echo "=== Gateway Logs ==="
grep "$REQUEST_ID" /tmp/janus-gateway.log | jq .

echo "=== Baseline Logs ==="
grep "$REQUEST_ID" /tmp/janus-baseline.log | jq .

echo "=== Sandy Logs ==="
grep "$REQUEST_ID" /tmp/sandy.log | jq .
```

## Acceptance Criteria

- [ ] All requests have unique request IDs
- [ ] Request IDs propagate through all services
- [ ] Structured JSON logging in all services
- [ ] Logs include service name, timestamp, request_id
- [ ] Timing information logged at key points
- [ ] Errors include full context
- [ ] UI shows request ID in debug mode
- [ ] Log search endpoint works
- [ ] CLI tool can search by request ID

## Files to Create/Modify

```
# Shared utilities (or copy to each service)
shared/
├── tracing.py           # NEW: Request ID utilities
└── logging_config.py    # NEW: Structured logging setup

gateway/janus_gateway/
├── middleware/
│   └── tracing.py       # NEW: Tracing middleware
├── routers/
│   └── debug.py         # MODIFY: Add log search
└── main.py              # MODIFY: Add middleware

baseline-agent-cli/janus_baseline_agent_cli/
├── middleware/
│   └── tracing.py       # NEW
└── main.py              # MODIFY

baseline-langchain/janus_baseline_langchain/
├── middleware/
│   └── tracing.py       # NEW
└── main.py              # MODIFY

ui/src/
└── components/
    └── chat/
        └── MessageFooter.tsx  # MODIFY: Show request ID

scripts/
└── log-search.sh        # NEW: Log search CLI
```

## Future Enhancements

1. **OpenTelemetry Integration**: Full distributed tracing with spans
2. **Log Aggregation Service**: Loki, Elasticsearch, or CloudWatch
3. **Dashboards**: Grafana dashboards for request flow visualization
4. **Alerts**: Automatic alerts on error rate spikes
5. **Sampling**: Sample verbose logs in production to reduce volume

## Related Specs

- Spec 93: Comprehensive Logging & Observability
- Spec 80: Debug Mode Flow Visualization
- Spec 13: Ops Observability

NR_OF_TRIES: 0
