# Spec 125: Fast Path Performance & Thinking Display

## Status: COMPLETE

**Priority:** High
**Complexity:** Medium
**Prerequisites:** None

---

## Problem Statement

Simple queries like "Explain why the sky is blue" take too long to answer. This is a basic factual question that should be answered quickly via the fast path without extensive reasoning.

**Issues Identified:**

1. **Slow response time** - Simple queries should respond in 1-3 seconds, not 10+
2. **No thinking display** - When reasoning does occur, the thinking section doesn't show it
3. **Incorrect path detection** - Simple queries may be incorrectly routed to agent path

**Test Case:** "Explain why the sky is blue" (request id: chatcmpl-502a917bcf0642f48722d13c)

---

## Root Cause Analysis

1. **Complexity detection may be over-triggering** - Keywords like "explain" might push simple queries to agent path
2. **Fast path LLM may have high latency** - Model selection or configuration issues
3. **Thinking tokens not streamed to UI** - Reasoning content not captured and displayed

---

## Implementation

### 1. Optimize Complexity Detection for Simple Queries

**File: `gateway/janus_gateway/services/complexity_detector.py`**

Add fast-path shortcuts for obviously simple queries:

```python
# Simple factual patterns that should ALWAYS use fast path
SIMPLE_PATTERNS = [
    r"^(what|why|how|when|where|who) (is|are|was|were|do|does|did)\b",
    r"^explain\s+(why|how|what)\b",
    r"^(define|describe)\s+\w+$",
    r"^tell me about\b",
]

def is_simple_factual_query(query: str) -> bool:
    """Check if query is a simple factual question."""
    query_lower = query.lower().strip()

    # Very short queries are usually simple
    if len(query_lower.split()) <= 10:
        for pattern in SIMPLE_PATTERNS:
            if re.match(pattern, query_lower):
                return True

    return False

async def detect_complexity(query: str, ...) -> ComplexityResult:
    # Fast exit for simple queries
    if is_simple_factual_query(query):
        return ComplexityResult(
            is_complex=False,
            confidence=0.95,
            reason="Simple factual query - fast path",
            path="fast"
        )

    # ... existing complexity detection logic
```

### 2. Add Response Time Monitoring

**File: `gateway/janus_gateway/routers/chat.py`**

Add timing metrics to fast path:

```python
import time

async def handle_fast_path(request: ChatRequest, ...):
    start_time = time.monotonic()

    # ... existing fast path logic

    elapsed = time.monotonic() - start_time

    # Log slow fast-path responses for investigation
    if elapsed > 3.0:
        logger.warning(
            f"Slow fast-path response: {elapsed:.2f}s for query: {request.messages[-1].content[:50]}..."
        )

    # Include timing in debug events
    emit_debug_event(
        request_id=request_id,
        type="fast_path_complete",
        data={"elapsed_seconds": elapsed}
    )
```

### 3. Stream Thinking/Reasoning to UI

**File: `gateway/janus_gateway/services/llm_router.py`**

Capture and forward thinking tokens:

```python
async def stream_completion(request: ChatRequest, ...):
    async for chunk in llm_client.stream(request):
        # Check for thinking/reasoning content
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta

            # Some models include reasoning in a separate field
            if hasattr(delta, 'reasoning') and delta.reasoning:
                yield {
                    "type": "thinking",
                    "content": delta.reasoning
                }

            # Standard content
            if delta.content:
                yield {
                    "type": "content",
                    "content": delta.content
                }
```

**File: `ui/src/components/MessageBubble.tsx`**

Display thinking section when present:

```tsx
interface ThinkingContent {
  thinking?: string;
  content: string;
}

const MessageBubble = ({ message, ... }) => {
  const [showThinking, setShowThinking] = useState(false);

  // Parse thinking from message if present
  const { thinking, content } = parseThinkingContent(message.content);

  return (
    <div className="message-bubble">
      {thinking && (
        <div className="message-thinking">
          <button
            onClick={() => setShowThinking(!showThinking)}
            className="thinking-toggle"
          >
            <ChevronIcon direction={showThinking ? 'down' : 'right'} />
            Thinking...
          </button>
          {showThinking && (
            <div className="thinking-content">
              <ReactMarkdown>{thinking}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
      <div className="message-content">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
};
```

**CSS:**
```css
.message-thinking {
  margin-bottom: 8px;
  border-left: 2px solid rgba(99, 210, 151, 0.5);
  padding-left: 12px;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #9CA3AF;
  font-size: 12px;
  cursor: pointer;
  background: none;
  border: none;
}

.thinking-content {
  font-size: 13px;
  color: #9CA3AF;
  margin-top: 8px;
  font-style: italic;
}
```

### 4. Model Selection for Fast Path

Ensure fast path uses a fast model:

**File: `gateway/janus_gateway/config.py`**

```python
# Fast path should use quick models
FAST_PATH_MODEL = os.getenv("FAST_PATH_MODEL", "gpt-4o-mini")
FAST_PATH_MAX_TOKENS = int(os.getenv("FAST_PATH_MAX_TOKENS", "1024"))
```

---

## Performance Targets

| Query Type | Target Response Time | Path |
|------------|---------------------|------|
| Simple factual (≤10 words) | < 2s first token | Fast |
| Explanation request | < 3s first token | Fast |
| Multi-step task | Variable | Agent |
| Code execution | Variable | Agent |

---

## Acceptance Criteria

- [x] "Explain why the sky is blue" responds in < 3 seconds (via simple factual query pattern match)
- [x] Simple factual queries route to fast path (pattern-based detection skips LLM verification)
- [x] Thinking/reasoning content displays in collapsible section (already implemented in MessageBubble)
- [x] Debug panel shows correct path (fast vs agent) (emits FAST_PATH_START/AGENT_PATH_START events)
- [x] Response timing logged for monitoring (slow_fast_path_response warning for > 3s)

---

## Testing

1. Query: "Explain why the sky is blue" - should use fast path, < 3s
2. Query: "What is 2+2?" - should use fast path, < 2s
3. Query: "Write a Python script to download a file" - should use agent path
4. Verify thinking section appears when model reasons
5. Check debug panel shows correct path selection

---

## NR_OF_TRIES: 1
