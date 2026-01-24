# Spec 25: LLM-Based Complexity Detection Second Pass

## Status: COMPLETE

## Context / Why

The current complexity detection in `baseline-agent-cli/janus_baseline_agent_cli/services/complexity.py` uses keyword matching as a fast first pass. While this is efficient, it can miss nuanced cases where:
- A request seems simple by keywords but actually needs agent capabilities
- A request contains keywords but is actually simple (false positives)

Adding an LLM-based second pass after the keyword check will improve routing accuracy while keeping latency low for obvious cases.

## Goals

- Add intelligent second pass using fast LLM (GLM-4.7-Flash) with tool calling
- Only invoke second pass when keyword check indicates "simple" (potential false negative)
- Use tool calling to get structured decision (not free-form text parsing)
- Keep total routing decision under 500ms for fast path cases

## Non-Goals

- Replace keyword-based detection (it remains the fast first pass)
- Use expensive models for routing decisions
- Add complexity to cases already correctly identified as complex

## Functional Requirements

### FR-1: Add Tool Calling Support to Models

Update `baseline-agent-cli/janus_baseline_agent_cli/models/openai.py` to support tool calling:

```python
class FunctionDefinition(BaseModel):
    """OpenAI function definition."""
    name: str
    description: str
    parameters: dict[str, Any]


class ToolDefinition(BaseModel):
    """OpenAI tool definition."""
    type: Literal["function"] = "function"
    function: FunctionDefinition


class FunctionCall(BaseModel):
    """Function call in tool_calls."""
    name: str
    arguments: str  # JSON string


class ToolCall(BaseModel):
    """Tool call in assistant message."""
    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class AssistantMessage(BaseModel):
    """Assistant message with optional tool calls."""
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
```

### FR-2: Create Routing Tool Definition

Define a `use_agent` tool for the LLM to call:

```python
USE_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "use_agent",
        "description": "Decide whether this request needs the agent sandbox with tools (for image generation, code execution, web search, etc.) or can be answered directly by LLM.",
        "parameters": {
            "type": "object",
            "properties": {
                "needs_agent": {
                    "type": "boolean",
                    "description": "True if request needs agent sandbox (image gen, code exec, web search, file ops). False if LLM can answer directly."
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of the decision"
                }
            },
            "required": ["needs_agent", "reason"],
            "additionalProperties": False
        }
    }
}
```

### FR-3: Implement Second Pass in ComplexityDetector

Add LLM-based second pass to `complexity.py`:

```python
import httpx
import json

ROUTING_MODEL = "zai-org/GLM-4.7-Flash"
ROUTING_PROMPT = """Analyze this user request and decide if it needs agent sandbox capabilities.

Agent sandbox is needed for:
- Image/video/audio generation (e.g., "generate an image of...", "create a video...")
- Code execution (e.g., "run this code", "execute...")
- Web search (e.g., "search for...", "find current...")
- File operations (e.g., "download...", "save to file...")
- Any task requiring external tools or APIs

Direct LLM response is sufficient for:
- General conversation and questions
- Explanations and summaries
- Simple math (without code)
- Writing assistance (without execution)

User request: {user_message}

Call the use_agent function with your decision."""


class ComplexityDetector:
    # ... existing code ...

    async def _llm_routing_check(self, text: str) -> tuple[bool, str]:
        """Second pass: Use LLM with tool calling to verify routing decision."""
        if not self._settings.openai_api_key:
            return False, "no_api_key"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://llm.chutes.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": ROUTING_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": ROUTING_PROMPT.format(user_message=text[:500])
                            }
                        ],
                        "tools": [USE_AGENT_TOOL],
                        "tool_choice": {
                            "type": "function",
                            "function": {"name": "use_agent"}
                        },
                        "max_tokens": 100,
                        "temperature": 0.0,
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Extract tool call
                message = data["choices"][0]["message"]
                if message.get("tool_calls"):
                    tool_call = message["tool_calls"][0]
                    args = json.loads(tool_call["function"]["arguments"])
                    return args.get("needs_agent", False), args.get("reason", "llm_decision")

                return False, "no_tool_call"

        except Exception as e:
            # On any error, fall back to fast path (don't block)
            return False, f"llm_check_error: {str(e)}"

    async def analyze_async(self, messages: list[Message]) -> ComplexityAnalysis:
        """Async version of analyze with optional LLM second pass."""
        # First pass: keyword-based (same as before)
        first_pass = self.analyze(messages)

        # If already complex, no need for second pass
        if first_pass.is_complex:
            return first_pass

        # Second pass only if enabled and first pass said "simple"
        if self._settings.enable_llm_routing:
            text = self._extract_text(messages[-1].content) if messages else ""
            needs_agent, reason = await self._llm_routing_check(text)

            if needs_agent:
                return ComplexityAnalysis(
                    is_complex=True,
                    reason=f"llm_second_pass: {reason}",
                    keywords_matched=first_pass.keywords_matched,
                    multimodal_detected=first_pass.multimodal_detected,
                    text_preview=first_pass.text_preview,
                )

        return first_pass
```

### FR-4: Add Configuration Setting

Add to `config.py`:

```python
enable_llm_routing: bool = Field(
    default=True,
    description="Enable LLM-based second pass for complexity detection",
)
llm_routing_model: str = Field(
    default="zai-org/GLM-4.7-Flash",
    description="Fast model to use for routing decisions",
)
llm_routing_timeout: float = Field(
    default=3.0,
    description="Timeout in seconds for LLM routing check",
)
```

### FR-5: Update Main.py to Use Async Analysis

Update `stream_response` in `main.py`:

```python
async def stream_response(...) -> AsyncGenerator[str, None]:
    # Use async analysis with optional LLM second pass
    analysis = await complexity_detector.analyze_async(request.messages)
    # ... rest unchanged ...
```

## Non-Functional Requirements

### NFR-1: Performance

- Keyword first pass: <5ms (unchanged)
- LLM second pass: <3s timeout (only for simple cases)
- Total routing: <3.5s worst case

### NFR-2: Reliability

- LLM check failures must not block requests
- Fall back to fast path on any error
- Log all routing decisions for debugging

### NFR-3: Cost

- Use cheapest fast model (GLM-4.7-Flash)
- Only call LLM for potential false negatives
- Limit input to 500 chars

## Acceptance Criteria

- [ ] "hello" → fast path (no LLM check, keywords say simple)
- [ ] "write code" → agent path (keywords, no LLM check needed)
- [ ] "can you make me a picture of a cat" → agent path (LLM second pass catches it if keywords miss)
- [ ] "what's the weather like today" → agent path if LLM recognizes need for web search
- [ ] LLM check timeout → defaults to fast path, no error shown to user
- [ ] Configuration to disable LLM routing works
- [ ] All routing decisions logged with reason

## Test Plan

### Unit Tests

```python
@pytest.mark.asyncio
async def test_llm_routing_catches_multimodal():
    detector = ComplexityDetector(settings)
    msgs = [Message(role="user", content="make me a picture of a sunset")]
    result = await detector.analyze_async(msgs)
    assert result.is_complex == True
    assert "llm_second_pass" in result.reason

@pytest.mark.asyncio
async def test_llm_routing_timeout_fallback():
    # Mock timeout
    detector = ComplexityDetector(settings)
    msgs = [Message(role="user", content="hello")]
    result = await detector.analyze_async(msgs)
    assert result.is_complex == False  # Falls back to fast path
```

## Files to Modify

- `baseline-agent-cli/janus_baseline_agent_cli/models/openai.py` - Add tool calling models
- `baseline-agent-cli/janus_baseline_agent_cli/services/complexity.py` - Add LLM second pass
- `baseline-agent-cli/janus_baseline_agent_cli/config.py` - Add routing config
- `baseline-agent-cli/janus_baseline_agent_cli/main.py` - Use async analysis

## Open Questions

1. Should we cache routing decisions for identical prompts?
2. Should tool_choice be "required" or "auto"? (Using required ensures we get a decision)
3. Rate limiting on the routing model?

## Related Specs

- Spec 24: Multimodal Request Routing (adds keywords, this adds LLM check)
- Spec 21: Enhanced Baseline Implementation
