# Spec 24: Multimodal Request Routing & Agent Path Activation

## Status: COMPLETE

## Context / Why

Currently, when users ask Janus Chat to generate images, create audio, or perform other multimodal tasks, the requests are routed to the "fast path" (direct LLM call) instead of the "complex path" (agent sandbox with tools).

**Example interaction:**
```
User: "can you generate me an image of a cat?"
Janus: "I can't generate images directly right now, but I can help you create a detailed prompt..."
```

This happens because:

1. **Complexity detector doesn't recognize multimodal tasks**: The `ComplexityDetector` class in `baseline/janus_baseline/services/complexity.py` only has coding-related keywords like "write code", "implement", "debug". It lacks keywords for:
   - Image generation ("generate image", "create picture", "draw")
   - Audio generation ("text to speech", "generate audio", "create voice")
   - Video generation ("create video", "generate animation")
   - Web research ("search the web", "research", "find information")

2. **Sandy sandbox not configured in production**: Even if routing worked, the agent path requires `SANDY_BASE_URL` environment variable to be set on the Render baseline service.

The agent pack already contains documentation for Chutes multimodal APIs:
- `agent-pack/models/text-to-image.md` - Qwen/HunYuan image generation
- `agent-pack/models/text-to-speech.md` - Kokoro TTS
- `agent-pack/models/text-to-video.md` - WAN-2/LTX video
- `agent-pack/models/lip-sync.md` - MuseTalk

The system prompt (`agent-pack/prompts/system.md`) tells the agent to use these docs. The infrastructure is there — the routing is just broken.

## Goals

- Enable Janus to handle multimodal generation requests (images, audio, video)
- Route requests that need tool access to the agent sandbox
- Configure Sandy integration in production
- Provide a consistent, capable AI assistant experience

## Non-Goals

- Implementing the actual image/audio/video generation (already in agent-pack docs)
- Changing the agent sandbox infrastructure
- Adding new Chutes API integrations (already documented)

## Functional Requirements

### FR-1: Expand Complexity Keywords

Add multimodal and research-related keywords to `COMPLEX_KEYWORDS` in `complexity.py`:

```python
COMPLEX_KEYWORDS = [
    # Existing coding keywords
    "write code",
    "create a file",
    "build",
    "implement",
    "develop",
    "debug",
    "fix the bug",
    "refactor",
    "run tests",
    "execute",
    "compile",
    "deploy",
    "install",
    "analyze this codebase",
    "modify the",
    "update the code",
    "create a script",
    "write a program",
    "generate code",

    # NEW: Image generation
    "generate image",
    "generate an image",
    "create image",
    "create an image",
    "create picture",
    "draw",
    "make a picture",
    "image of",
    "picture of",
    "illustration of",
    "photo of",
    "render",

    # NEW: Audio generation
    "text to speech",
    "generate audio",
    "create audio",
    "speak this",
    "say this",
    "read aloud",
    "voice",
    "tts",

    # NEW: Video generation
    "generate video",
    "create video",
    "make a video",
    "animate",
    "animation",

    # NEW: Research and web tasks
    "search the web",
    "search online",
    "research",
    "find information",
    "look up",
    "what is the latest",
    "current news",
    "recent developments",

    # NEW: File and data tasks
    "download",
    "fetch",
    "scrape",
    "extract data",
    "parse",
    "convert file",
]
```

### FR-2: Add Multimodal Detection Method

Add a dedicated method to detect multimodal requests:

```python
MULTIMODAL_KEYWORDS = [
    "image", "picture", "photo", "illustration", "draw", "render",
    "audio", "voice", "speech", "sound", "speak", "tts",
    "video", "animate", "animation", "clip",
]

def _is_multimodal_request(self, text: str) -> bool:
    """Check if request involves multimodal generation."""
    text_lower = text.lower()
    generation_verbs = ["generate", "create", "make", "produce", "render"]

    for verb in generation_verbs:
        for media in self.MULTIMODAL_KEYWORDS:
            if verb in text_lower and media in text_lower:
                return True

    return False
```

Update `is_complex()` to check this:

```python
def is_complex(self, messages: list[Message]) -> tuple[bool, str]:
    # ... existing checks ...

    # Check for multimodal request
    if self._is_multimodal_request(text):
        return True, "multimodal_request"

    # ... rest of method ...
```

### FR-3: Configure Sandy in Production

Add `SANDY_BASE_URL` environment variable to the Render baseline service:

```
SANDY_BASE_URL=https://sandy.chutes.ai  # or appropriate Sandy endpoint
SANDY_API_KEY=<sandy-api-key>           # if authentication required
```

### FR-4: Add "Always Agent" Mode (Optional)

For maximum capability, add a configuration option to always use the agent path:

```python
# In config.py
always_use_agent: bool = Field(
    default=False,
    description="Always route to agent sandbox, bypass complexity detection"
)

# In main.py stream_response()
if settings.always_use_agent or (is_complex and sandy_service.is_available):
    # Use agent path
```

This allows operators to enable full agent capabilities for all requests.

### FR-5: Improve Complexity Logging

Enhance logging to help debug routing decisions:

```python
logger.info(
    "complexity_check",
    is_complex=is_complex,
    reason=reason,
    keywords_matched=[k for k in self.COMPLEX_KEYWORDS if k in text_lower],
    multimodal_detected=self._is_multimodal_request(text),
    sandy_available=sandy_service.is_available,
    text_preview=text[:100],
)
```

## Non-Functional Requirements

### NFR-1: Backward Compatibility

- Existing coding-related requests must continue to work
- Simple chat requests should still use the fast path for low latency

### NFR-2: Performance

- Complexity detection should remain fast (<5ms)
- Keyword matching should use efficient string operations

### NFR-3: Observability

- Log all routing decisions with reasons
- Track multimodal request success/failure rates

## Acceptance Criteria

- [ ] "generate me an image of a cat" routes to agent path (is_complex=True, reason=multimodal_request)
- [ ] "create a picture of a sunset" routes to agent path
- [ ] "text to speech: hello world" routes to agent path
- [ ] "search the web for latest news" routes to agent path
- [ ] "hello, how are you?" still uses fast path (is_complex=False)
- [ ] Sandy is configured in production (SANDY_BASE_URL set)
- [ ] Agent can successfully generate images using Chutes APIs
- [ ] Routing decisions are logged with detailed reasons

## Test Plan

### Unit Tests

```python
def test_multimodal_detection():
    detector = ComplexityDetector(settings)

    # Should detect as complex
    assert detector.is_complex([Message(role="user", content="generate an image of a cat")])[0] == True
    assert detector.is_complex([Message(role="user", content="create a picture of sunset")])[0] == True
    assert detector.is_complex([Message(role="user", content="text to speech: hello")])[0] == True
    assert detector.is_complex([Message(role="user", content="search the web for python docs")])[0] == True

    # Should remain simple
    assert detector.is_complex([Message(role="user", content="hello")])[0] == False
    assert detector.is_complex([Message(role="user", content="what is 2+2")])[0] == False
```

### Integration Test

```bash
# With Sandy configured
curl -X POST https://janus-gateway.../v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"baseline","messages":[{"role":"user","content":"generate an image of a cat"}],"stream":true}'

# Should see:
# - reasoning_content: "Starting complex task execution..."
# - reasoning_content: "Creating Sandy sandbox..."
# - content: actual image data or URL
```

## Files to Modify

- `baseline/janus_baseline/services/complexity.py` - Add keywords and multimodal detection
- `baseline/janus_baseline/main.py` - Add optional always-agent mode
- `baseline/janus_baseline/config.py` - Add always_use_agent setting
- Render environment variables - Add SANDY_BASE_URL

## Dependencies

- Sandy sandbox service must be available and accessible
- Chutes multimodal APIs must be operational
- Agent pack docs must be accurate and up-to-date

## Open Questions

1. **Sandy endpoint**: What is the production Sandy URL? Is authentication required?
2. **Rate limits**: Are there rate limits on Sandy sandbox creation?
3. **Cost tracking**: How do we track/attribute Sandy usage costs?
4. **Fallback**: If Sandy is unavailable, should we fall back to fast path with explanation?

## Related Specs

- Spec 21: Enhanced Baseline Implementation (agent pack creation)
- Spec 09: Reference Implementation CLI Agent Baseline
