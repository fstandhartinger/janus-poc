# Spec 80: Debug Mode Flow Visualization

## Status: COMPLETE
**Priority:** Medium
**Complexity:** Very High
**Prerequisites:** Spec 79

---

## Overview

Add a debug mode to the chat UI that visualizes the internal execution flow of the selected baseline in real-time. When activated:

1. Shows a Mermaid diagram of the baseline's architecture
2. Highlights the current execution step in the diagram
3. Displays real-time info: which path taken, agent actions, created files, etc.
4. Requires additional SSE endpoints on baselines for debug info streaming

---

## Functional Requirements

### FR-1: Debug Button in Chat UI

Add a "Debug" toggle button in the chat header.

```tsx
// components/chat/DebugToggle.tsx
export function DebugToggle({ enabled, onToggle }: DebugToggleProps) {
  return (
    <button
      onClick={() => onToggle(!enabled)}
      className={cn(
        "p-2 rounded-lg transition-colors",
        enabled
          ? "text-orange-400 bg-orange-500/20"
          : "text-gray-400 hover:text-gray-300"
      )}
      title={enabled ? "Debug mode ON" : "Debug mode OFF"}
    >
      <Bug className="w-5 h-5" />
    </button>
  );
}
```

### FR-2: Debug Panel Layout

When debug mode is enabled, show a split view with debug panel.

```tsx
// components/chat/DebugPanel.tsx
export function DebugPanel({
  baseline,
  debugState,
  onClose,
}: DebugPanelProps) {
  return (
    <div className="w-[500px] h-full border-l border-white/10 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <h3 className="font-medium flex items-center gap-2">
          <Bug className="w-4 h-4 text-orange-400" />
          Debug: {baseline}
        </h3>
        <button onClick={onClose}>
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Mermaid Diagram */}
      <div className="flex-1 overflow-auto p-4">
        <DebugFlowDiagram
          baseline={baseline}
          currentStep={debugState.currentStep}
          highlightedNodes={debugState.activeNodes}
        />
      </div>

      {/* Status Log */}
      <div className="h-[200px] border-t border-white/10 overflow-auto">
        <DebugLog events={debugState.events} />
      </div>
    </div>
  );
}
```

### FR-3: Real-Time Mermaid Diagram

Display the baseline's architecture with highlighted current step.

```tsx
// components/debug/DebugFlowDiagram.tsx
import mermaid from 'mermaid';

interface DebugFlowDiagramProps {
  baseline: 'agent-cli' | 'langchain';
  currentStep: string;
  highlightedNodes: string[];
}

export function DebugFlowDiagram({
  baseline,
  currentStep,
  highlightedNodes,
}: DebugFlowDiagramProps) {
  const [svg, setSvg] = useState<string>('');

  const diagramDefinition = useMemo(() => {
    return generateDiagram(baseline, currentStep, highlightedNodes);
  }, [baseline, currentStep, highlightedNodes]);

  useEffect(() => {
    mermaid.render('debug-diagram', diagramDefinition).then(({ svg }) => {
      setSvg(svg);
    });
  }, [diagramDefinition]);

  return (
    <div
      className="debug-diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

function generateDiagram(
  baseline: string,
  currentStep: string,
  activeNodes: string[],
): string {
  // Base diagram with style classes for highlighting
  const diagram = `
    flowchart TB
      classDef active fill:#63D297,stroke:#63D297,color:#000
      classDef inactive fill:#1a1a2e,stroke:#333
      classDef pending fill:#1a1a2e,stroke:#666,stroke-dasharray: 5 5

      subgraph Request ["Incoming Request"]
          REQ["POST /v1/chat/completions"]
      end

      subgraph Routing ["Complexity Detection"]
          DETECT["Complexity Detector"]
          KEYWORDS["Keyword Check"]
          LLM_VERIFY["LLM Verification"]
      end

      subgraph FastPath ["Fast Path"]
          FAST_LLM["Direct LLM Call"]
      end

      subgraph AgentPath ["Agent Path"]
          SANDY["Sandy Sandbox"]
          AGENT["CLI Agent"]
      end

      subgraph Tools ["Agent Tools"]
          TOOL_IMG["Image Gen"]
          TOOL_CODE["Code Exec"]
          TOOL_SEARCH["Web Search"]
          TOOL_FILES["File Ops"]
      end

      subgraph Response ["Response"]
          SSE["SSE Stream"]
      end

      REQ --> DETECT
      DETECT --> KEYWORDS
      KEYWORDS -->|"Complex"| SANDY
      KEYWORDS -->|"Simple"| LLM_VERIFY
      LLM_VERIFY --> FAST_LLM
      LLM_VERIFY --> SANDY
      SANDY --> AGENT
      AGENT --> TOOL_IMG & TOOL_CODE & TOOL_SEARCH & TOOL_FILES
      FAST_LLM --> SSE
      AGENT --> SSE

      %% Apply classes based on active nodes
      ${activeNodes.map(node => `class ${node} active`).join('\n')}
  `;
  return diagram;
}
```

### FR-4: Debug Event Log

Show real-time events in a scrollable log.

```tsx
// components/debug/DebugLog.tsx
interface DebugEvent {
  timestamp: string;
  type: 'info' | 'step' | 'tool' | 'error';
  message: string;
  data?: Record<string, unknown>;
}

export function DebugLog({ events }: { events: DebugEvent[] }) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [events]);

  return (
    <div ref={logRef} className="font-mono text-xs p-2 space-y-1">
      {events.map((event, i) => (
        <div
          key={i}
          className={cn(
            "flex gap-2",
            event.type === 'error' && "text-red-400",
            event.type === 'step' && "text-moss-400",
            event.type === 'tool' && "text-blue-400",
          )}
        >
          <span className="text-gray-500">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
          <span className="text-gray-400">[{event.type}]</span>
          <span>{event.message}</span>
        </div>
      ))}
    </div>
  );
}
```

### FR-5: Debug SSE Endpoint on Baselines

Add `/v1/debug/stream` endpoint that streams debug events.

```python
# baseline-agent-cli/janus_baseline_agent_cli/routers/debug.py
from fastapi import APIRouter
from sse_starlette import EventSourceResponse

router = APIRouter(prefix="/v1/debug", tags=["debug"])

@router.get("/stream/{request_id}")
async def stream_debug(request_id: str):
    """Stream debug events for a specific request."""
    async def event_generator():
        async for event in debug_event_queue.subscribe(request_id):
            yield {
                "event": "debug",
                "data": event.model_dump_json(),
            }
    return EventSourceResponse(event_generator())
```

### FR-6: Debug Event Types

Define debug event types that baselines can emit.

```python
# models/debug.py
from enum import Enum
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
    step: str  # Node ID in Mermaid diagram
    message: str
    data: dict | None = None
```

### FR-7: Debug Event Emission in Baseline

Emit debug events at key points in execution.

```python
# services/debug.py
import asyncio
from collections import defaultdict

class DebugEventQueue:
    def __init__(self):
        self.queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def emit(self, request_id: str, event: DebugEvent):
        """Emit a debug event for a request."""
        await self.queues[request_id].put(event)

    async def subscribe(self, request_id: str):
        """Subscribe to debug events for a request."""
        queue = self.queues[request_id]
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
                yield event
        except asyncio.TimeoutError:
            pass
        finally:
            del self.queues[request_id]

debug_queue = DebugEventQueue()

# Usage in main.py
async def stream_response(request: ChatCompletionRequest):
    request_id = generate_request_id()

    # Emit: Request received
    await debug_queue.emit(request_id, DebugEvent(
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
        type=DebugEventType.REQUEST_RECEIVED,
        step="REQ",
        message="Request received",
        data={"model": request.model, "message_count": len(request.messages)},
    ))

    # Emit: Complexity check start
    await debug_queue.emit(request_id, DebugEvent(
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
        type=DebugEventType.COMPLEXITY_CHECK_START,
        step="DETECT",
        message="Starting complexity analysis",
    ))

    analysis = await complexity_detector.analyze_async(request.messages)

    # Emit: Complexity result
    await debug_queue.emit(request_id, DebugEvent(
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
        type=DebugEventType.COMPLEXITY_CHECK_COMPLETE,
        step="DETECT",
        message=f"Complexity: {'complex' if analysis.is_complex else 'simple'}",
        data={"is_complex": analysis.is_complex, "reason": analysis.reason},
    ))

    if analysis.is_complex:
        # Emit: Agent path
        await debug_queue.emit(request_id, DebugEvent(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            type=DebugEventType.AGENT_PATH_START,
            step="SANDY",
            message="Routing to agent path",
        ))
        # ... continue with agent execution, emitting events
    else:
        # Emit: Fast path
        await debug_queue.emit(request_id, DebugEvent(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            type=DebugEventType.FAST_PATH_START,
            step="FAST_LLM",
            message="Routing to fast path",
        ))
```

### FR-8: Gateway Debug Proxy

Gateway proxies debug stream from baseline.

```python
# gateway/janus_gateway/routers/debug.py
from fastapi import APIRouter
from sse_starlette import EventSourceResponse
import httpx

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/stream/{request_id}")
async def proxy_debug_stream(request_id: str, baseline: str = "agent-cli"):
    """Proxy debug stream from baseline."""
    baseline_url = get_baseline_url(baseline)

    async def event_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{baseline_url}/v1/debug/stream/{request_id}",
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        yield {"event": "debug", "data": line[5:].strip()}

    return EventSourceResponse(event_generator())
```

### FR-9: UI Debug State Management

Manage debug state with real-time updates.

```tsx
// hooks/useDebug.ts
export function useDebug(enabled: boolean, requestId: string | null) {
  const [debugState, setDebugState] = useState<DebugState>({
    currentStep: '',
    activeNodes: [],
    events: [],
    files: [],
  });

  useEffect(() => {
    if (!enabled || !requestId) return;

    const eventSource = new EventSource(
      `/api/debug/stream/${requestId}?baseline=${selectedBaseline}`
    );

    eventSource.onmessage = (event) => {
      const debugEvent = JSON.parse(event.data) as DebugEvent;

      setDebugState((prev) => ({
        currentStep: debugEvent.step,
        activeNodes: computeActiveNodes(debugEvent),
        events: [...prev.events, debugEvent],
        files: debugEvent.type === 'file_created'
          ? [...prev.files, debugEvent.data?.filename]
          : prev.files,
      }));
    };

    return () => eventSource.close();
  }, [enabled, requestId]);

  return debugState;
}

function computeActiveNodes(event: DebugEvent): string[] {
  // Return list of nodes that should be highlighted
  // based on current execution path
  const pathMap: Record<string, string[]> = {
    'REQ': ['REQ'],
    'DETECT': ['REQ', 'DETECT'],
    'KEYWORDS': ['REQ', 'DETECT', 'KEYWORDS'],
    'LLM_VERIFY': ['REQ', 'DETECT', 'KEYWORDS', 'LLM_VERIFY'],
    'FAST_LLM': ['REQ', 'DETECT', 'KEYWORDS', 'LLM_VERIFY', 'FAST_LLM'],
    'SANDY': ['REQ', 'DETECT', 'KEYWORDS', 'SANDY'],
    'AGENT': ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT'],
    // ... etc
  };
  return pathMap[event.step] || [event.step];
}
```

### FR-10: Files Created List

Show files created by agent in debug panel.

```tsx
// components/debug/DebugFiles.tsx
export function DebugFiles({ files }: { files: string[] }) {
  if (files.length === 0) return null;

  return (
    <div className="p-2 border-t border-white/10">
      <h4 className="text-xs text-gray-400 mb-1">Created Files:</h4>
      <div className="space-y-1">
        {files.map((file) => (
          <div key={file} className="text-xs flex items-center gap-1">
            <FileIcon className="w-3 h-3" />
            {file}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Technical Requirements

### TR-1: Baseline Debug Support

Each baseline must:
1. Accept optional `debug: true` in request body
2. Expose `/v1/debug/stream/{request_id}` SSE endpoint
3. Emit debug events at key execution points
4. Return `request_id` in response headers

### TR-2: Gateway Requirements

1. Proxy debug SSE stream from baseline
2. Track which baseline is handling which request

### TR-3: UI Requirements

1. Debug toggle in header
2. Split panel layout when debug enabled
3. Real-time Mermaid rendering with highlighting
4. Event log with auto-scroll
5. File list display

---

## Files to Create

| File | Purpose |
|------|---------|
| `ui/src/components/debug/DebugPanel.tsx` | Main debug panel |
| `ui/src/components/debug/DebugFlowDiagram.tsx` | Mermaid diagram renderer |
| `ui/src/components/debug/DebugLog.tsx` | Event log component |
| `ui/src/components/debug/DebugFiles.tsx` | Created files list |
| `ui/src/components/debug/DebugToggle.tsx` | Debug mode toggle |
| `ui/src/hooks/useDebug.ts` | Debug state management |
| `baseline-agent-cli/.../routers/debug.py` | Debug SSE endpoint |
| `baseline-agent-cli/.../services/debug.py` | Debug event queue |
| `baseline-agent-cli/.../models/debug.py` | Debug event types |
| `baseline-langchain/.../routers/debug.py` | Debug SSE endpoint |
| `baseline-langchain/.../services/debug.py` | Debug event queue |
| `gateway/janus_gateway/routers/debug.py` | Debug proxy |

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/components/ChatArea.tsx` | Add debug toggle, split layout |
| `ui/src/app/chat/page.tsx` | Debug state management |
| `baseline-agent-cli/.../main.py` | Emit debug events |
| `baseline-langchain/.../main.py` | Emit debug events |
| `gateway/janus_gateway/main.py` | Include debug router |

---

## UI/UX Design

### Normal View

```
┌─────────────────────────────────────────────────────┐
│ [Model ▼] [Memory 🧠] [Debug 🐛]               User │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Chat messages...                                   │
│                                                     │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [+] Write a message...                       [Send] │
└─────────────────────────────────────────────────────┘
```

### Debug View (Split)

```
┌─────────────────────────────────────┬───────────────────────┐
│ [Model ▼] [Memory 🧠] [Debug 🐛*]   │ 🐛 Debug: agent-cli X │
├─────────────────────────────────────┼───────────────────────┤
│                                     │  ┌─────────────────┐  │
│  Chat messages...                   │  │ [Mermaid        │  │
│                                     │  │  Diagram with   │  │
│                                     │  │  highlighted    │  │
│                                     │  │  current step]  │  │
│                                     │  └─────────────────┘  │
│                                     ├───────────────────────┤
│                                     │ 12:34:56 [step] REQ   │
│                                     │ 12:34:57 [step] DETECT│
│                                     │ 12:34:58 [info] ...   │
├─────────────────────────────────────┼───────────────────────┤
│ [+] Write a message...       [Send] │ Files: output.png     │
└─────────────────────────────────────┴───────────────────────┘
```

### Mermaid Diagram States

**Idle:** All nodes gray/dim
**Active:** Current node green, previous nodes in path lighter green
**Complete:** All traversed nodes green, final node bright green

---

## Acceptance Criteria

- [ ] Debug toggle button in chat header
- [ ] Debug panel shows when enabled
- [ ] Mermaid diagram renders correctly
- [ ] Current step is highlighted in diagram
- [ ] Events appear in real-time in log
- [ ] Files created by agent are listed
- [ ] Debug SSE endpoint works on baselines
- [ ] Gateway proxies debug stream correctly
- [ ] Panel can be closed
- [ ] Debug mode persists across page refresh (optional)

---

## Testing Checklist

- [ ] Debug toggle works
- [ ] Panel opens/closes correctly
- [ ] Simple query shows fast path in diagram
- [ ] Complex query shows agent path in diagram
- [ ] Tool calls show up in event log
- [ ] Created files appear in file list
- [ ] Diagram updates in real-time
- [ ] Works with agent-cli baseline
- [ ] Works with langchain baseline
- [ ] No performance degradation when debug disabled

---

## Notes

- Debug mode adds latency due to event emission
- Debug endpoint should be optional (disabled in production)
- Consider adding rate limiting to debug stream
- Mermaid re-rendering on each event may be expensive - consider debouncing
- File list could include download links in future
- Consider adding timing info (how long each step took)

NR_OF_TRIES: 1
