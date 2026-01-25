# Spec 109: Agentic Chat Response E2E Verification

## Status: NOT STARTED

## Context / Why

During testing of spec 100 (long agentic task reliability), we observed that:
1. The timeout fix works - connections hold for 5+ minutes
2. The agent sandbox starts correctly (sandbox created, Claude Code running)
3. The "thinking" reasoning content appears in the UI
4. **BUT: The actual response content is NOT appearing in the chat**

This is a critical issue - users see "Working on your request..." in the thinking panel but never get the actual answer. The agent may be completing work but the response is not being streamed back to the UI properly.

## Goals

- Diagnose why agent responses aren't appearing in the chat UI
- Fix the streaming pipeline so agent responses display correctly
- Add E2E smoke test that verifies agent responses appear
- Ensure both reasoning_content AND content are displayed properly

## Investigation Areas

### Area 1: Sandy Service Response Parsing

Check `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py`:
- Is the agent response being parsed correctly?
- Are `content` vs `reasoning_content` being handled properly?
- Is the SSE stream being forwarded correctly?

### Area 2: Gateway SSE Forwarding

Check `gateway/janus_gateway/routers/chat.py`:
- Is the SSE keepalive interfering with actual content?
- Are all SSE chunks being forwarded?
- Is the `data: [DONE]` terminator being sent?

### Area 3: UI Parsing

Check `ui/src/lib/api.ts` and `ui/src/components/ChatArea.tsx`:
- Is the UI parsing `content` vs `reasoning_content` correctly?
- Is there a display issue vs a data issue?
- Check browser console for parsing errors

## Functional Requirements

### FR-1: Verify Sandy Agent Output

```python
# Add logging to sandy.py to capture raw agent output
async def execute_via_agent_api(self, request, debug_emitter=None):
    # ... existing code ...
    async for line in response.aiter_lines():
        logger.debug("sandy_raw_line", line=line[:200])  # Log first 200 chars
        # ... parse and yield ...
```

### FR-2: E2E Smoke Test

```python
# tests/e2e/test_agentic_chat.py

import pytest
import httpx
import json

GATEWAY_URL = "https://janus-gateway-bqou.onrender.com"

@pytest.mark.asyncio
async def test_agentic_response_has_content():
    """Verify agent responses include actual content, not just reasoning."""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "What is 2+2? Just answer with the number."}],
                "stream": True,
            },
        )

        assert response.status_code == 200

        content_parts = []
        reasoning_parts = []

        async for line in response.aiter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                    if delta.get("reasoning_content"):
                        reasoning_parts.append(delta["reasoning_content"])
                except json.JSONDecodeError:
                    pass

        full_content = "".join(content_parts)
        full_reasoning = "".join(reasoning_parts)

        # Must have SOME content (not just reasoning)
        assert len(full_content) > 0, f"No content received. Reasoning was: {full_reasoning[:500]}"
        assert "4" in full_content, f"Expected '4' in response, got: {full_content}"


@pytest.mark.asyncio
async def test_agent_code_execution():
    """Verify agent can execute code and return results."""
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "Run: print('HELLO_TEST_123')"}],
                "stream": True,
            },
        )

        assert response.status_code == 200

        full_content = ""
        async for line in response.aiter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        full_content += delta["content"]
                except json.JSONDecodeError:
                    pass

        assert "HELLO_TEST_123" in full_content, f"Expected output not found in: {full_content[:500]}"
```

### FR-3: Browser Console Check

Add error boundary and logging to ChatArea:

```typescript
// In ChatArea.tsx - add to SSE parsing
try {
  const parsed = JSON.parse(data) as ChatStreamEvent;
  console.log('[SSE] Received chunk:', {
    hasContent: !!parsed.choices?.[0]?.delta?.content,
    hasReasoning: !!parsed.choices?.[0]?.delta?.reasoning_content,
    content: parsed.choices?.[0]?.delta?.content?.slice(0, 100),
  });
  // ... rest of parsing
} catch (e) {
  console.error('[SSE] Parse error:', e, 'Raw data:', data.slice(0, 200));
}
```

## Acceptance Criteria

- [ ] Agent responses appear in chat (not just in "Thinking" panel)
- [ ] Simple prompts like "What is 2+2?" get visible answers
- [ ] Code execution tasks show output in chat
- [ ] E2E test passes: `pytest tests/e2e/test_agentic_chat.py -v`
- [ ] No SSE parsing errors in browser console
- [ ] Response includes both reasoning (collapsed) and content (visible)

## Debugging Commands

```bash
# Test directly against baseline
curl -X POST https://janus-baseline-agent.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"What is 2+2?"}],"stream":true}' \
  2>/dev/null | head -50

# Test through gateway
curl -X POST https://janus-gateway-bqou.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"baseline-cli-agent","messages":[{"role":"user","content":"What is 2+2?"}],"stream":true}' \
  2>/dev/null | head -50
```

## Files to Investigate/Modify

```
baseline-agent-cli/janus_baseline_agent_cli/
├── services/sandy.py         # Agent response streaming
├── main.py                   # SSE generation
└── streaming.py              # Stream optimization

gateway/janus_gateway/
├── routers/chat.py           # SSE forwarding

ui/src/
├── lib/api.ts                # SSE parsing
├── components/ChatArea.tsx   # Response display
└── hooks/useChat.ts          # State management
```

## Related Specs

- Spec 100: Long Agentic Task Reliability (timeout fix - DONE)
- Spec 80: Debug Mode Flow Visualization

NR_OF_TRIES: 0
