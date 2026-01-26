# Spec 93: Comprehensive Logging & Observability

## Status: COMPLETE
**Priority:** Critical
**Complexity:** High
**Prerequisites:** None

---

## Overview

This spec ensures all architecture components (Sandy, Gateway, UI, baseline-agent-cli, baseline-langchain) have comprehensive logging that is accessible and understandable. When an agentic run happens, we must be able to trace what happened at every step.

### Current Architecture (PoC Target)

Logging covers this architecture:

```
USER → UI → Gateway (Render) → baseline-agent-cli (Render) → Sandy agent/run API → Agent
                             → baseline-langchain (Render) → LangChain Agent
```

Each component must log with correlation IDs so we can trace a request end-to-end.

### Background (from Investigation)

The investigation revealed that debugging agent issues was difficult due to:
1. Insufficient logging of agent selection decisions
2. Missing SSE event logging
3. No visibility into what prompt actually reached the agent
4. Sandy sandbox logs not easily accessible
5. No correlation IDs to trace requests across services

---

## Functional Requirements

### FR-1: Request Correlation

Every request should have a correlation ID that flows through all services.

```python
# shared/correlation.py (or in each service)

import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

def get_or_create_correlation_id(headers: dict) -> str:
    """Get correlation ID from headers or create new one."""
    correlation_id = headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)
    return correlation_id

def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get() or str(uuid.uuid4())
```

### FR-2: Gateway Logging

```python
# gateway/janus_gateway/logging_config.py

import structlog
from datetime import datetime

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

logger = structlog.get_logger()

# Required log events in gateway:
#
# 1. request_received
#    - correlation_id, method, path, model, message_preview
#
# 2. routing_decision
#    - correlation_id, target_baseline, reason
#
# 3. baseline_request
#    - correlation_id, baseline_url, timeout
#
# 4. baseline_response
#    - correlation_id, status_code, response_preview, duration_ms
#
# 5. sse_chunk_forwarded
#    - correlation_id, chunk_type, chunk_preview
#
# 6. request_complete
#    - correlation_id, total_duration_ms, success
```

### FR-3: Baseline Agent CLI Logging

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/debug.py

from enum import Enum
import structlog

class DebugEventType(Enum):
    # Request lifecycle
    REQUEST_RECEIVED = "request_received"
    COMPLEXITY_ANALYSIS = "complexity_analysis"
    ROUTING_DECISION = "routing_decision"

    # Fast path
    FAST_PATH_START = "fast_path_start"
    FAST_PATH_LLM_CALL = "fast_path_llm_call"
    FAST_PATH_CHUNK = "fast_path_chunk"
    FAST_PATH_COMPLETE = "fast_path_complete"

    # Agent path
    AGENT_PATH_START = "agent_path_start"
    AGENT_SELECTION = "agent_selection"
    MODEL_SELECTION = "model_selection"

    # Sandy interaction
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

    # Tool usage (from SSE events)
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"

    # Artifacts
    ARTIFACT_CREATED = "artifact_created"

    # Errors
    ERROR = "error"

logger = structlog.get_logger()

async def emit_debug_event(
    event_type: DebugEventType,
    correlation_id: str,
    **kwargs
):
    """Emit a structured debug event."""
    logger.info(
        event_type.value,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow().isoformat(),
        **kwargs
    )
```

### FR-4: Sandy Logging

```python
# sandy/sandy/logging.py

# Required log events in Sandy:
#
# 1. sandbox_create_request
#    - correlation_id, requested_image, timeout
#
# 2. sandbox_created
#    - correlation_id, sandbox_id, container_id
#
# 3. agent_run_request
#    - correlation_id, sandbox_id, agent_type, model, prompt_preview
#
# 4. agent_binary_found
#    - correlation_id, agent_type, binary_path, yolo_flags
#
# 5. agent_process_start
#    - correlation_id, command, env_vars_preview
#
# 6. agent_stdout_line
#    - correlation_id, line_preview (truncated to 200 chars)
#
# 7. agent_tool_call
#    - correlation_id, tool_name, arguments_preview
#
# 8. agent_tool_result
#    - correlation_id, tool_name, result_preview
#
# 9. agent_process_complete
#    - correlation_id, exit_code, duration_ms
#
# 10. sandbox_terminate
#     - correlation_id, sandbox_id, reason
```

### FR-5: UI Logging

```typescript
// ui/src/lib/logger.ts

interface LogEvent {
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  event: string;
  correlationId?: string;
  data?: Record<string, unknown>;
}

const logs: LogEvent[] = [];

export function log(event: string, data?: Record<string, unknown>) {
  const logEvent: LogEvent = {
    timestamp: new Date().toISOString(),
    level: 'info',
    event,
    correlationId: getCurrentCorrelationId(),
    data,
  };

  logs.push(logEvent);

  // Also log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[${logEvent.event}]`, logEvent.data);
  }
}

// Required log events in UI:
//
// 1. chat_message_sent
//    - correlation_id, message_preview, model
//
// 2. sse_connection_opened
//    - correlation_id, url
//
// 3. sse_event_received
//    - correlation_id, event_type, data_preview
//
// 4. sse_content_chunk
//    - correlation_id, chunk_length, total_length
//
// 5. sse_reasoning_chunk
//    - correlation_id, chunk_length
//
// 6. sse_artifact_received
//    - correlation_id, artifact_type, artifact_name
//
// 7. sse_connection_closed
//    - correlation_id, reason, total_chunks
//
// 8. chat_response_complete
//    - correlation_id, response_length, artifacts_count, duration_ms
```

### FR-6: Log Aggregation Endpoint

Add an endpoint to retrieve logs for a specific correlation ID.

```python
# gateway/janus_gateway/routers/debug.py

from fastapi import APIRouter

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/logs/{correlation_id}")
async def get_logs_for_request(correlation_id: str):
    """
    Retrieve all logs for a specific request across services.

    Returns logs from:
    - Gateway
    - Baseline (CLI or LangChain)
    - Sandy (if applicable)
    """
    # In production, this would query a log aggregation service
    # For now, return what we can from local logs
    pass

@router.get("/recent")
async def get_recent_logs(limit: int = 100):
    """Get most recent log entries."""
    pass
```

### FR-7: Debug Mode UI

Add a debug panel to the UI to view logs in real-time.

```typescript
// ui/src/components/DebugPanel.tsx

interface DebugPanelProps {
  correlationId: string;
  visible: boolean;
}

export function DebugPanel({ correlationId, visible }: DebugPanelProps) {
  const [logs, setLogs] = useState<LogEvent[]>([]);

  useEffect(() => {
    if (visible && correlationId) {
      // Fetch logs for this request
      fetchLogs(correlationId).then(setLogs);
    }
  }, [correlationId, visible]);

  return (
    <div className="debug-panel glass-card">
      <h3>Request Debug: {correlationId}</h3>
      <div className="log-entries">
        {logs.map((log, i) => (
          <div key={i} className={`log-entry log-${log.level}`}>
            <span className="timestamp">{log.timestamp}</span>
            <span className="event">{log.event}</span>
            <pre className="data">{JSON.stringify(log.data, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### FR-8: Render Log Access

Document how to access logs via Render MCP and CLI.

```bash
# Via Render CLI
render logs --service janus-gateway --tail 100

# Via Render MCP in Claude Code
# Use the render MCP tools to:
# 1. list_services
# 2. list_logs with service_id and label filters

# Filter for specific correlation ID
render logs --service janus-baseline-agent-cli | grep "correlation_id=abc123"
```

---

## Log Event Matrix

| Component | Event | When | Key Data |
|-----------|-------|------|----------|
| **Gateway** | request_received | Request arrives | model, message_preview |
| | routing_decision | Route selected | target_baseline, reason |
| | baseline_request | Forwarding | baseline_url |
| | sse_chunk_forwarded | Each chunk | chunk_type |
| | request_complete | Done | duration_ms, success |
| **Baseline CLI** | complexity_analysis | After analysis | is_complex, keywords, llm_decision |
| | routing_decision | Fast vs Agent | path, reason |
| | agent_selection | Agent chosen | agent_type, binary_path |
| | model_selection | Model chosen | model, reason |
| | sandy_agent_api_request | Calling Sandy | prompt_preview, agent, model |
| | sandy_agent_api_sse_event | Each SSE event | event_type, data_preview |
| | tool_call_start | Agent uses tool | tool_name, arguments |
| | tool_call_result | Tool returns | tool_name, result_preview |
| | artifact_created | Artifact ready | type, name, url |
| **Sandy** | sandbox_created | Container ready | sandbox_id |
| | agent_binary_found | Agent located | binary_path, yolo_flags |
| | agent_process_start | Agent starts | command |
| | agent_stdout_line | Agent output | line_preview |
| | agent_process_complete | Agent done | exit_code, duration_ms |
| **UI** | chat_message_sent | User sends | message_preview |
| | sse_event_received | Each SSE | event_type |
| | chat_response_complete | Done | duration_ms, artifacts_count |

---

## Acceptance Criteria

### Correlation IDs
- [ ] Every request gets a correlation ID
- [ ] Correlation ID passes through Gateway → Baseline → Sandy
- [ ] Logs can be filtered by correlation ID

### Gateway Logging
- [ ] All 5 required events logged
- [ ] Logs include correlation ID
- [ ] Logs are structured JSON

### Baseline CLI Logging
- [ ] All debug events logged
- [ ] Complexity analysis decision logged
- [ ] Agent selection decision logged
- [ ] Model selection decision logged
- [ ] Sandy SSE events logged
- [ ] Tool calls logged

### Sandy Logging
- [ ] Sandbox lifecycle logged
- [ ] Agent process logged
- [ ] Stdout/stderr captured
- [ ] Tool calls visible

### UI Logging
- [ ] Client-side events logged
- [ ] SSE events tracked
- [ ] Debug panel available

### Log Access
- [ ] Render logs accessible via MCP
- [ ] Logs filterable by correlation ID
- [ ] Debug endpoint works

---

## Testing Procedure

### 1. Make Test Request

```bash
# Note the correlation ID in response headers
curl -v -X POST https://janus-gateway.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-$(date +%s)" \
  -d '{
    "model": "baseline-agent-cli",
    "messages": [{"role": "user", "content": "Clone a repo and summarize it"}],
    "stream": false
  }'
```

### 2. Retrieve Logs

```bash
# Get Gateway logs
render logs --service janus-gateway | grep "test-1234567890"

# Get Baseline logs
render logs --service janus-baseline-agent-cli | grep "test-1234567890"

# Get Sandy logs
render logs --service sandy | grep "test-1234567890"
```

### 3. Verify Log Content

Check that logs show:
1. Request received at Gateway
2. Routed to baseline-agent-cli
3. Complexity analysis result
4. Agent selection (claude-code)
5. Model selection
6. Sandy API call
7. Agent execution events
8. Tool calls if any
9. Response complete

---

## Files to Create

| File | Purpose |
|------|---------|
| `gateway/janus_gateway/logging_config.py` | Structured logging setup |
| `gateway/janus_gateway/routers/debug.py` | Debug/logs endpoint |
| `baseline-agent-cli/janus_baseline_agent_cli/services/debug.py` | Debug event emitter |
| `baseline-langchain/janus_baseline_langchain/services/debug.py` | Debug event emitter |
| `ui/src/lib/logger.ts` | Client-side logging |
| `ui/src/components/DebugPanel.tsx` | Debug UI panel |

## Files to Modify

| File | Changes |
|------|---------|
| `gateway/janus_gateway/main.py` | Add correlation ID middleware |
| `gateway/janus_gateway/routers/chat.py` | Add logging calls |
| `baseline-agent-cli/janus_baseline_agent_cli/main.py` | Add logging calls |
| `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` | Add SSE event logging |
| `sandy/sandy/api/routes.py` | Add logging calls |
| `sandy/sandy/agent.py` | Add agent execution logging |
| `ui/src/components/ChatArea.tsx` | Add logging calls |

---

## Notes

- Use structured logging (JSON) for machine parsing
- Truncate long values in logs to prevent bloat
- Consider log levels: DEBUG for verbose, INFO for key events
- Production may need log rotation
- Consider adding Sentry or similar for error tracking
- Debug panel should only be visible in development or for admin users

---

## Related Specs

- Spec 92: Baseline Agent CLI E2E Verification (uses logging to debug)
- Spec 94: Baseline LangChain E2E Verification (needs same logging)
- Spec 80: Debug Mode Flow Visualization (builds on this)

NR_OF_TRIES: 0
