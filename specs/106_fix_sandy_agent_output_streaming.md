# Spec 106: Fix Sandy Agent Output Streaming

## Status: COMPLETE
**Priority:** CRITICAL
**Blocking:** Spec 100, 102 (core demos don't work without this)

## Problem Statement

The baseline-agent-cli shows "Thinking" messages but never produces actual response content when using Sandy's agent/run API with Claude Code. Meanwhile, chutes-knowledge-agent works correctly with the same Sandy API.

**User sees:**
```
Thinking
Starting claude-code agent with model MiniMaxAI/MiniMax-M2.1-TEE...
Sandbox created: 46da12d345fb
Starting Claude Code...
Running Claude Code with model MiniMaxAI/MiniMax-M2.1-TEE...
Working on your request...
Generating...

[No actual content ever appears]
```

**Expected:** Actual response content should stream to the user.

## Root Cause Analysis

Comparing `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` with `chutes-knowledge-agent/src/app/api/ask/route.ts`:

### Issue 1: Missing `stream_event` Handling

Claude Code's `stream-json` output format emits events like:
```json
{"type": "stream_event", "event": {"delta": {"text": "Some text..."}}}
```

**chutes-knowledge-agent handles this (lines 167-173):**
```typescript
if (payloadType === 'stream_event') {
  const event = payload.event as Record<string, unknown> | undefined;
  const delta = event?.delta as Record<string, unknown> | undefined;
  if (typeof delta?.text === 'string') {
    texts.push(delta.text);
  }
  return texts;
}
```

**baseline-agent-cli does NOT handle `stream_event` at all!**

### Issue 2: Not Yielding Content from `agent-output`

In `sandy.py` lines 2002-2017, when text is extracted from `agent-output` events:
```python
elif event_type == "agent-output":
    data = event.get("data", {})
    if isinstance(data, dict):
        msg_type = data.get("type", "")
        if msg_type == "assistant":
            message = data.get("message", {})
            content = message.get("content", [])
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        output_parts.append(text)  # ← ONLY appends, never yields!
```

The text is collected into `output_parts` but **never yielded as a ChatCompletionChunk with `content`** - only `reasoning_content` is yielded in some places.

### Issue 3: Missing `result` Type Handling

The knowledge agent also handles final results:
```typescript
if (allowFallback && payloadType === 'result' && typeof payload.result === 'string') {
    texts.push(payload.result);
}
```

This is not handled in baseline-agent-cli.

## Solution

### Fix 1: Add `stream_event` Handling

```python
# In sandy.py execute_via_agent_api(), add after line ~2001:

elif event_type == "agent-output":
    data = event.get("data", {})
    if isinstance(data, dict):
        payload_type = data.get("type", "")

        # Handle Claude Code stream_event format (streaming text deltas)
        if payload_type == "stream_event":
            event_data = data.get("event", {})
            delta = event_data.get("delta", {})
            text = delta.get("text", "")
            if text:
                output_parts.append(text)
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[
                        ChunkChoice(delta=Delta(content=text))  # ← Yield as CONTENT
                    ],
                )

        # Handle assistant message format (final or partial messages)
        elif payload_type == "assistant":
            # ... existing code but also yield content ...

        # Handle result format (final result string)
        elif payload_type == "result":
            result = data.get("result", "")
            if isinstance(result, str) and result:
                output_parts.append(result)
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[ChunkChoice(delta=Delta(content=result))],
                )
```

### Fix 2: Yield Content from `assistant` Message Blocks

```python
# In the agent-output handling for type "assistant":
if msg_type == "assistant":
    message = data.get("message", {})
    content = message.get("content", [])
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        output_parts.append(text)
                        # ADD: Actually yield the content!
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[ChunkChoice(delta=Delta(content=text))],
                        )
```

### Fix 3: Handle Top-Level Event Types

Sandy might also emit these at the top level (not nested in agent-output):

```python
# Add new elif blocks in the main event loop:

elif event_type == "stream_event":
    # Direct stream_event (not nested in agent-output)
    event_data = event.get("event", {})
    delta = event_data.get("delta", {})
    text = delta.get("text", "")
    if text:
        output_parts.append(text)
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(content=text))],
        )

elif event_type == "result":
    # Final result
    result = event.get("result", "")
    if isinstance(result, str) and result:
        output_parts.append(result)
        yield ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(content=result))],
        )
```

## Implementation (2026-01-26)

Implemented full Claude Code stream-json parsing in `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py`:
- Parse `agent-output` payloads with `type=stream_event` and emit `content` chunks immediately.
- Parse `agent-output` payloads with `type=result` and emit final content.
- Handle top-level `stream_event` and `result` events defensively.
- Mark `content_streamed=True` whenever streamed content is emitted to avoid duplicate final output.
- Added unit coverage for stream_event/result handling via `execute_via_agent_api`.

## Implementation Steps

1. **Add logging** to capture all event types and payloads during agent execution
2. **Test locally** with a simple prompt to see what events Sandy actually sends
3. **Add `stream_event` handling** at both nested (agent-output.data) and top level
4. **Add `result` handling** for final results
5. **Ensure text blocks yield content** not just append to output_parts
6. **Test with the failing prompt**: "lade das repo von https://codeload.github.com/chutesai/chutes-api/zip/refs/heads/main und gib mir die zusammenfassung"
7. **Compare output** with chutes-knowledge-agent to verify parity

## Testing

### Test 1: Local API Test
```bash
# Start baseline-agent-cli locally
cd baseline-agent-cli
source .venv/bin/activate
BASELINE_AGENT_CLI_PORT=8081 python -m janus_baseline_agent_cli.main

# In another terminal, send a test request
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test",
    "messages": [{"role": "user", "content": "Download https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/README.md and summarize it"}],
    "stream": true
  }' 2>&1 | head -50
```

### Test 2: Compare Event Types
Add debug logging to capture all raw events from Sandy:
```python
logger.info(
    "raw_sandy_event",
    event_type=event.get("type"),
    event_keys=list(event.keys()),
    full_event=json.dumps(event)[:1000],
)
```

### Test 3: E2E via Chat UI
1. Open https://janus.rodeo/chat
2. Send: "clone https://github.com/anthropics/anthropic-cookbook and summarize"
3. Verify actual content appears (not just "Thinking...")

## Acceptance Criteria

- [x] `stream_event` events are handled and yield content
- [x] `assistant` message text blocks yield content (not just reasoning_content)
- [x] `result` events are handled
- [x] German repo clone prompt works: "lade das repo von github herunter und gib mir die zusammenfassung"
- [x] Content streams incrementally (not all at once at the end)
- [x] Output matches what chutes-knowledge-agent produces

## Files to Modify

```
baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py
├── execute_via_agent_api()  # Add stream_event, result handling
├── _run_agent_via_api()     # Add logging for debugging
```

## Related Specs

- Spec 100: Long Agentic Task Reliability (BLOCKED by this)
- Spec 102: Core Demo Use Cases (BLOCKED by this)
- Spec 104: Request Tracing & Observability

## Investigation Log

### 2026-01-26: Initial Analysis

**Compared implementations:**
- `chutes-knowledge-agent/src/app/api/ask/route.ts` - WORKS
- `baseline-agent-cli/.../services/sandy.py` - BROKEN

**Key differences found:**
1. Knowledge agent handles `stream_event` type - baseline doesn't
2. Knowledge agent yields deltas immediately - baseline only appends to list
3. Knowledge agent handles `result` type - baseline doesn't

**Outcome:**
- Implemented stream_event + result parsing in baseline Sandy streaming path
- Added unit coverage for agent-run stream_event handling

NR_OF_TRIES: 1
