# Spec 100: Long Agentic Task Reliability

## Status: COMPLETE

### Completed (2026-01-25):
- [x] Extended UI timeout from 30s to 600s (10 min)
- [x] Extended gateway request_timeout from 300s to 600s
- [x] Extended baseline sandy_timeout from 300s to 600s
- [x] Verified SSE keepalives working (`: ping` visible)
- [x] Verified fast path works (simple queries get responses)
- [x] Verified connections hold for 5+ minutes

### Completed (2026-01-29):
- [x] Agent path response content verified (see spec 109)
- [x] Added keepalive/progress updates for long-running operations
- [x] Added retry handling for timeouts and long-task integration tests

## Context / Why

Complex agentic tasks like "lade das chutes-api repo von github herunter und gib mir eine zusammenfassung" (download the chutes-api repo from github and give me a summary) currently fail or timeout. These are exactly the tasks that showcase Janus's value proposition - handling complex multi-step operations that require:

1. Repository cloning (network + filesystem)
2. File traversal and reading
3. Analysis and summarization
4. Streaming progress back to user

Currently these tasks fail due to:
- Timeout issues (default timeouts too short)
- SSE connection drops
- No intermediate progress feedback
- Error recovery not implemented

## Goals

- Make long-running agentic tasks reliable
- Provide continuous feedback during execution
- Handle errors gracefully with recovery
- Test with real-world complex prompts

## Functional Requirements

### FR-1: Extended Timeouts

```python
# baseline-agent-cli/janus_baseline_agent_cli/config.py

class Settings(BaseSettings):
    # Increase default timeouts for agentic tasks
    sandy_agent_timeout: int = 600  # 10 minutes (was 120)
    http_client_timeout: int = 660  # Slightly more than agent timeout
    sse_keepalive_interval: int = 15  # Send keepalive every 15s
```

```python
# In main.py - ensure timeouts are properly set
async def stream_agent_response(request: ChatCompletionRequest):
    timeout = httpx.Timeout(
        connect=30.0,
        read=settings.http_client_timeout,
        write=30.0,
        pool=30.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        # ... stream from Sandy
```

### FR-2: SSE Keepalive During Long Operations

```python
# Ensure continuous SSE stream even when agent is working silently

async def stream_with_keepalive(
    agent_stream: AsyncIterator[str],
    keepalive_interval: int = 15,
) -> AsyncIterator[str]:
    """Wrap agent stream with keepalives to prevent connection drops."""

    last_event = time.time()

    async def keepalive_generator():
        nonlocal last_event
        while True:
            await asyncio.sleep(keepalive_interval)
            if time.time() - last_event > keepalive_interval:
                yield 'data: {"choices":[{"delta":{"reasoning_content":"..."}}]}\n\n'

    keepalive_task = asyncio.create_task(keepalive_generator())

    try:
        async for chunk in agent_stream:
            last_event = time.time()
            yield chunk
    finally:
        keepalive_task.cancel()
```

### FR-3: Progress Indicators for Known Long Operations

```python
# In agent system prompt or tool definitions

LONG_OPERATION_INDICATORS = {
    "git clone": "Cloning repository...",
    "npm install": "Installing dependencies...",
    "pip install": "Installing Python packages...",
    "downloading": "Downloading file...",
    "analyzing": "Analyzing content...",
}

# Agent should emit reasoning_content during long ops
async def emit_progress(operation: str):
    indicator = LONG_OPERATION_INDICATORS.get(operation, "Working...")
    yield create_reasoning_chunk(indicator)
```

### FR-4: Graceful Error Recovery

```python
# Handle common failure modes

async def execute_with_retry(
    sandy_client: SandyClient,
    request: AgentRequest,
    max_retries: int = 2,
) -> AsyncIterator[str]:
    """Execute agent request with retry on recoverable errors."""

    for attempt in range(max_retries + 1):
        try:
            async for chunk in sandy_client.execute(request):
                yield chunk
            return  # Success
        except httpx.ReadTimeout:
            if attempt < max_retries:
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                yield create_reasoning_chunk(
                    f"Operation taking longer than expected, retrying..."
                )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                yield create_error_chunk(
                    "The operation timed out. The task may be too complex. "
                    "Try breaking it into smaller steps."
                )
                return
        except SandyUnavailableError:
            yield create_error_chunk(
                "Agent sandbox is temporarily unavailable. Please try again."
            )
            return
```

### FR-5: Test Suite for Long Tasks

```python
# tests/integration/test_long_agentic_tasks.py

import pytest
from janus_baseline_agent_cli.main import app
from httpx import AsyncClient

LONG_TASK_PROMPTS = [
    # German: Download repo and summarize
    {
        "prompt": "lade das chutes-api repo von github herunter und gib mir eine zusammenfassung",
        "expected_contains": ["chutes", "api", "repository"],
        "min_time_seconds": 30,
        "max_time_seconds": 300,
    },
    # English: Clone and analyze
    {
        "prompt": "clone https://github.com/anthropics/claude-code and summarize the README",
        "expected_contains": ["claude", "code"],
        "min_time_seconds": 20,
        "max_time_seconds": 180,
    },
    # Multi-step research
    {
        "prompt": "search for the latest Bittensor TAO price, then search for recent Bittensor news, and give me a summary",
        "expected_contains": ["TAO", "price", "Bittensor"],
        "min_time_seconds": 30,
        "max_time_seconds": 120,
    },
    # File creation task
    {
        "prompt": "create a Python script that fetches the top 5 Hacker News stories and saves them to a file",
        "expected_artifact": True,
        "min_time_seconds": 20,
        "max_time_seconds": 120,
    },
]

@pytest.mark.asyncio
@pytest.mark.parametrize("task", LONG_TASK_PROMPTS)
async def test_long_agentic_task(task):
    """Test that long agentic tasks complete successfully."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        start_time = time.time()

        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-agent-cli",
                "messages": [{"role": "user", "content": task["prompt"]}],
                "stream": True,
            },
            timeout=task["max_time_seconds"] + 30,
        )

        assert response.status_code == 200

        content = ""
        reasoning = ""
        has_artifact = False

        async for line in response.aiter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                data = json.loads(line[6:])
                delta = data.get("choices", [{}])[0].get("delta", {})
                content += delta.get("content", "")
                reasoning += delta.get("reasoning_content", "")
                if "artifact" in str(delta):
                    has_artifact = True

        elapsed = time.time() - start_time

        # Verify timing
        assert elapsed >= task["min_time_seconds"], "Task completed too quickly - may not have done actual work"
        assert elapsed <= task["max_time_seconds"], f"Task took too long: {elapsed}s"

        # Verify content
        for expected in task.get("expected_contains", []):
            assert expected.lower() in content.lower(), f"Expected '{expected}' in response"

        # Verify artifact if expected
        if task.get("expected_artifact"):
            assert has_artifact, "Expected artifact in response"

        # Verify we got reasoning (progress) during execution
        assert len(reasoning) > 0, "Expected reasoning/progress content during long task"


@pytest.mark.asyncio
async def test_sse_keepalive_during_long_task():
    """Verify SSE connection stays alive during long operations."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-agent-cli",
                "messages": [{"role": "user", "content": "clone a small github repo and list its files"}],
                "stream": True,
            },
            timeout=180,
        )

        last_event_time = time.time()
        max_gap = 0

        async for line in response.aiter_lines():
            now = time.time()
            gap = now - last_event_time
            max_gap = max(max_gap, gap)
            last_event_time = now

        # Should never have more than 30s gap (with 15s keepalive)
        assert max_gap < 30, f"SSE gap too large: {max_gap}s"
```

### FR-6: UI Timeout Handling

```typescript
// In ChatArea.tsx or useChat hook

const LONG_TASK_TIMEOUT = 10 * 60 * 1000; // 10 minutes

async function sendMessage(content: string) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, LONG_TASK_TIMEOUT);

  try {
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify({ ... }),
      signal: controller.signal,
    });

    // ... handle streaming response
  } catch (error) {
    if (error.name === 'AbortError') {
      // Show user-friendly timeout message
      appendMessage({
        role: 'assistant',
        content: 'The task took too long and was stopped. Try breaking it into smaller steps.',
      });
    }
  } finally {
    clearTimeout(timeoutId);
  }
}
```

## Acceptance Criteria

- [ ] "lade das chutes-api repo von github herunter" completes successfully
- [ ] "clone and summarize" tasks work reliably
- [ ] SSE connection maintained during long operations (no gaps > 30s)
- [ ] User sees progress/reasoning during execution
- [ ] Graceful error messages on timeout/failure
- [ ] Test suite for long tasks passes
- [ ] UI handles long tasks without freezing

## Files to Modify

```
baseline-agent-cli/janus_baseline_agent_cli/
├── config.py              # MODIFY: Increase timeouts
├── main.py                # MODIFY: Keepalive, retry logic
└── tests/
    └── integration/
        └── test_long_tasks.py  # NEW

ui/src/
├── hooks/useChat.ts       # MODIFY: Extended timeout
└── components/ChatArea.tsx  # MODIFY: Progress UI
```

## Testing Commands

```bash
# Run long task tests
cd baseline-agent-cli
pytest tests/integration/test_long_tasks.py -v --timeout=600

# Manual test
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"lade das chutes-api repo von github herunter und gib mir eine zusammenfassung"}],"stream":true}'
```

## Related Specs

- Spec 90: Complexity Detection Improvements (German keywords)
- Spec 97: CLI Agent Warm Pool
- Spec 92: Baseline Agent CLI E2E Verification

NR_OF_TRIES: 1
