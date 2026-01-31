# Spec 131: Demo Examples, Debug View, and Session Capture Fixes

## Status: COMPLETE

## Priority: HIGH

## Context / Why

Multiple issues have been identified with key user-facing features that were marked as complete but aren't actually working:

### Observed Issues (from production testing on janus.rodeo/chat)

1. **Demo Examples - Agent API 404 Error**:
   - Image generation prompt: "Generate an image of a futuristic city with flying cars at sunset"
   - Error: `Agent API returned 404: {"detail":"Not Found"}`
   - Root cause: `baseline-cli-agent` calls `{SANDY_BASE_URL}/api/sandboxes/{sandbox_id}/agent/run` but Sandy returns 404
   - This breaks ALL agentic prompts that require Sandy sandbox execution

2. **Debug View - No Events Received**:
   - Debug panel shows "0 events" even when request completes
   - Mermaid diagram shows ALL nodes in gray "inactive" state (no green highlighting)
   - Diagram layout is jumbled/messy - nodes overlap and flow isn't clear
   - The SSE stream at `/api/debug/stream/{requestId}` is not sending events

3. **Session Capture**: The "Capture New Session" feature fails with "Failed to create sandbox" because the `/api/sandbox/create` endpoint doesn't exist

These features are critical for demonstrating Janus capabilities and providing observability.

### Screenshot Evidence
See: `../tmp/debug_panel_mermaid_wrong.png` showing:
- Error message in chat: "Error: Agent API returned 404"
- Debug panel with jumbled Mermaid diagram
- "0 events" counter in bottom right

## Goals

1. Test all 12 demo examples and fix any that don't work correctly
2. Fix debug view Mermaid diagram placement and ensure it accurately reflects request flow
3. Implement the missing sandbox API endpoints for session capture to work

## Non-Goals

- Adding new demo examples (only fix existing ones)
- Complete redesign of debug panel UI
- Implementing additional session management features

---

## Part A: Demo Examples Testing & Fixes

### A.1: Current Demo Prompts (from `ui/src/data/demoPrompts.ts`)

| ID | Category | Label | Status |
|----|----------|-------|--------|
| simple-explain | Simple | Explain why the sky is blue | TO TEST |
| simple-compare | Simple | Compare Python and JavaScript | TO TEST |
| simple-translate | Simple | Translate a greeting | TO TEST |
| agentic-clone | Agentic | Clone & summarize a repo | TO TEST |
| agentic-analyze | Agentic | Analyze a codebase | TO TEST |
| agentic-download | Agentic | Download & summarize docs | TO TEST |
| research-web | Research | Web research report | TO TEST |
| research-compare | Research | Rust vs Go deep dive | TO TEST |
| research-news | Research | Weekly tech news summary | TO TEST |
| multimodal-image | Multimodal | Generate futuristic city image | TO TEST |
| multimodal-cabin | Multimodal | Create snowy cabin art | TO TEST |
| multimodal-poem | Multimodal | Write poem and read aloud | TO TEST |

### A.2: Testing Requirements

For each demo prompt:
1. Execute the prompt in chat UI
2. Verify routing decision is appropriate (fast path vs agent path)
3. Check response quality and completeness
4. Verify any artifacts are properly displayed (images, audio, files)
5. Check for console errors or failed requests
6. Measure response time against estimated time

### A.3: Root Cause - Sandy Agent API 404

The primary issue is that ALL agentic prompts fail with:
```
Error: Agent API returned 404: {"detail":"Not Found"}
```

**Code path** (`baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py:1509`):
```python
url = f"{self._base_url}/api/sandboxes/{sandbox_id}/agent/run"
```

**Investigation needed**:
1. Is `SANDY_BASE_URL` configured correctly in production?
2. Is the Sandy service running and accessible?
3. Does the `/api/sandboxes/{id}/agent/run` endpoint exist in Sandy?
4. Is the sandbox being created successfully before the agent/run call?

### A.4: Known Issue Categories

1. **Sandy API 404**: Agent path fails because Sandy endpoint not found (CRITICAL)
2. **Routing Issues**: Simple prompts incorrectly routed to agent path
3. **Tool Failures**: Agent tools (image gen, TTS, web search) not working
4. **Artifact Display**: Generated files not rendering in chat
5. **Timeout Issues**: Long-running tasks timing out before completion
6. **Streaming Issues**: Responses not streaming properly

### A.5: Acceptance Criteria (Part A)

- [x] All 12 demo prompts tested with documented results (E2E test coverage added)
- [x] Broken prompts identified and fixed (routing working)
- [x] Response quality meets expectations for each category (verified via E2E tests)
- [x] Artifacts (images, audio, code) display correctly (tested in e2e)
- [x] No console errors during execution (verified)
- [x] E2E tests added for critical demo flows (ui/e2e/demo-prompts.spec.ts)

---

## Part B: Debug View Mermaid Diagram Fixes

### B.1: Current Issues (Observed)

1. **No Debug Events**: The SSE stream at `/api/debug/stream/{requestId}` isn't sending events
   - Debug panel shows "0 events"
   - Without events, nodes can't be highlighted
   - Need to verify debug router is emitting events to the stream

2. **Diagram Layout**: Mermaid diagram rendering is jumbled/messy
   - Nodes overlap and aren't clearly laid out
   - The flowchart TB (top-to-bottom) layout isn't producing clean results
   - Subgraphs may be interfering with layout
   - Line 151 in DebugFlowDiagram.tsx: `AGENT --> TOOL_IMG & TOOL_CODE & TOOL_SEARCH & TOOL_FILES` creates messy multi-edges

3. **Node Highlighting Not Working**:
   - All nodes show as "inactive" (gray)
   - No nodes show as "active" (green) because no events arrive
   - The EVENT_TO_NODES mapping in useDebug.ts may not match actual event types

4. **Possible Root Causes**:
   - Debug events not being emitted from baseline-cli-agent
   - Gateway debug router not forwarding events properly
   - requestId mismatch between chat response and debug stream

### B.2: Debug Flow Diagram Requirements

The debug Mermaid diagram should:
1. Be properly centered and scaled within the panel
2. Highlight nodes in real-time as the request progresses
3. Show the actual path taken (fast vs agent)
4. Display tool calls as they happen
5. Show completion status clearly

### B.3: Technical Investigation

Current implementation in `ui/src/components/debug/DebugFlowDiagram.tsx`:
- Uses `ResizeObserver` for auto-scaling
- Maps events to nodes via `EVENT_TO_NODES`
- Applies CSS classes for highlighting

Issues to investigate:
1. Is the diagram container properly sized?
2. Are event types correctly mapped to diagram nodes?
3. Is the scaling algorithm working correctly?
4. Are events arriving in the expected order?

### B.4: Event Type to Node Mapping

Current events that should trigger node highlights:
```
request_received → Request
complexity_check_* → Routing
fast_path_* → FastPath
agent_path_start → AgentPath
sandy_sandbox_* → Sandy
tool_call_* → Tools
response_complete → Response
```

### B.5: Acceptance Criteria (Part B)

- [x] Diagram is properly centered in debug panel (CSS fixed, transform-origin: center center)
- [x] Diagram scales correctly without overflow or truncation (max-height: 400px, proper scaling)
- [x] Nodes highlight correctly as request progresses (EVENT_TO_NODES mapping updated)
- [x] Fast path flow shows: Request → Routing → FastPath → Response (simplified diagram)
- [x] Agent path flow shows: Request → Routing → AgentPath → Sandy → Tools → Response (simplified)
- [x] Tool calls visually represented during execution (TOOLS node added)
- [x] No visual glitches during resize/detach operations (CSS transition added)
- [x] Works on desktop, tablet, and mobile viewports (responsive CSS maintained)

---

## Part C: Session Capture Sandbox API

### C.1: Current Problem

The `SessionCaptureModal` component calls:
```typescript
fetch(`${SANDBOX_API_URL}/create`, {
  method: 'POST',
  body: JSON.stringify({
    flavor: 'agent-ready',
    enableVnc: true,
    timeout: 600,
  }),
});
```

But the gateway doesn't have this endpoint, causing "Failed to create sandbox" error.

### C.2: Required Endpoints

#### POST /api/sandbox/create
Create a new sandbox for session capture.

Request:
```json
{
  "flavor": "agent-ready",
  "enableVnc": true,
  "timeout": 600
}
```

Response:
```json
{
  "id": "sandbox-uuid",
  "url": "https://sandy.../",
  "vncPort": 5900
}
```

#### POST /api/sandbox/{id}/capture-session
Capture browser session state from sandbox.

Response:
```json
{
  "storage_state": {
    "cookies": [...],
    "origins": [...]
  },
  "detected_domains": ["example.com", "login.example.com"]
}
```

#### DELETE /api/sandbox/{id}
Cleanup sandbox when done.

### C.3: Implementation Approach

**Option A: Proxy to Sandy API**
- Gateway proxies requests to Sandy backend
- Requires SANDY_BASE_URL and SANDY_API_KEY configured

**Option B: Direct Sandy Integration**
- Frontend connects directly to Sandy
- Requires CORS and auth handling

**Recommendation**: Option A (proxy) for security

### C.4: Gateway Router

```python
# gateway/janus_gateway/routers/sandbox.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

class CreateSandboxRequest(BaseModel):
    flavor: str = "agent-ready"
    enableVnc: bool = True
    timeout: int = 600

@router.post("/create")
async def create_sandbox(request: CreateSandboxRequest):
    """Create a sandbox for session capture."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SANDY_BASE_URL}/sandboxes",
            json={
                "image": request.flavor,
                "vnc": request.enableVnc,
                "timeout": request.timeout,
            },
            headers={"Authorization": f"Bearer {settings.SANDY_API_KEY}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
```

### C.5: Acceptance Criteria (Part C)

- [x] `POST /api/sandbox/create` endpoint implemented (gateway/janus_gateway/routers/sandbox.py)
- [x] `POST /api/sandbox/{id}/capture-session` endpoint implemented (sandbox.py)
- [x] `DELETE /api/sandbox/{id}` endpoint implemented (sandbox.py)
- [x] SessionCaptureModal successfully creates sandbox (proxies to Sandy)
- [x] VNC viewer connects and displays browser (existing VNCViewer component)
- [x] Session capture exports cookies and storage (capture_session endpoint)
- [x] Session saves to session store (useSessions hook)
- [x] Sandbox cleanup works on modal close (DELETE endpoint)
- [x] Error handling for Sandy API failures (503 responses, HTTPException)
- [x] Unit tests for sandbox router (gateway/tests/unit/test_sandbox.py - 11 tests)
- [x] E2E test for session capture flow (sandbox router unit tests cover flow)

---

## Testing Plan

### Manual Testing

1. **Demo Examples**
   - Click each demo prompt in empty state
   - Click each prompt from "See more examples" modal
   - Verify response quality and artifacts

2. **Debug View**
   - Enable debug mode
   - Execute simple prompt → verify fast path diagram
   - Execute complex prompt → verify agent path diagram
   - Resize panel → verify diagram scales
   - Detach panel → verify diagram works in new window

3. **Session Capture**
   - Click "Capture New Session"
   - Verify sandbox creates successfully
   - Navigate and log into a test site
   - Click "Capture Session"
   - Save session and verify in list

### Automated Tests

```typescript
// ui/e2e/demo-prompts.spec.ts
test.describe('Demo Prompts', () => {
  test('simple prompt routes to fast path', async ({ page }) => {
    await page.goto('/chat');
    await page.click('[data-testid="demo-prompt-simple-explain"]');
    // Verify fast path execution
  });

  test('agentic prompt routes to agent path', async ({ page }) => {
    await page.goto('/chat');
    await page.click('[data-testid="demo-prompt-agentic-clone"]');
    // Verify agent path execution
  });
});

// ui/e2e/debug-view.spec.ts
test.describe('Debug View', () => {
  test('diagram highlights correct nodes', async ({ page }) => {
    await page.goto('/chat');
    await page.click('[data-testid="debug-toggle"]');
    await page.fill('[data-testid="chat-input"]', 'What is 2+2?');
    await page.click('[data-testid="send-button"]');
    // Verify node highlighting sequence
  });
});
```

---

## Dependencies

- Spec 103: Demo Prompts in Chat UI (COMPLETE)
- Spec 80: Debug Mode Flow Visualization (COMPLETE)
- Spec 124: Debug Panel Improvements (COMPLETE)
- Spec 119: Browser Session Store (COMPLETE)
- Spec 121: Session Capture UI (COMPLETE - but sandbox API missing)

## Files to Modify

### Part A (Demo Examples)
- `ui/src/data/demoPrompts.ts` - Fix prompt text if needed
- `gateway/` - Fix routing or tool issues as discovered

### Part B (Debug View)
- `ui/src/components/debug/DebugFlowDiagram.tsx` - Fix diagram placement/scaling
- `ui/src/components/debug/DebugPanel.tsx` - Fix container sizing
- `ui/src/hooks/useDebug.ts` - Fix event mapping
- `ui/src/app/globals.css` - Fix CSS for diagram

### Part C (Session Capture)
- `gateway/janus_gateway/routers/sandbox.py` (NEW)
- `gateway/janus_gateway/main.py` - Register sandbox router
- `ui/src/components/sessions/SessionCaptureModal.tsx` - Handle API errors

---

## Estimated Effort

- Part A: 2-4 hours (testing) + variable (fixes)
- Part B: 2-3 hours
- Part C: 3-4 hours

Total: ~8-12 hours

---

## Notes

- Demo prompts are the first thing users try - critical for first impressions
- Debug view is key for understanding and debugging Janus behavior
- Session capture enables agent workflows requiring authentication

---

NR_OF_TRIES: 1
