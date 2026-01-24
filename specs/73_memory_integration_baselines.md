# Spec 73: Memory Integration for Baseline Implementations

**Status:** NOT STARTED
**Priority:** High
**Complexity:** Medium
**Prerequisites:** Spec 72 (Memory Service Backend)

---

## Overview

Integrate the memory system into both baseline Janus implementations (baseline-agent-cli and baseline-langchain). This involves:
1. Accepting `user_id` and `enable_memory` in incoming requests
2. Fetching relevant memories before processing
3. Injecting memory context into prompts
4. Calling memory extraction API after response completes

---

## Functional Requirements

### FR-1: Extended Request Model

Add optional fields to `ChatCompletionRequest`:

```python
class ChatCompletionRequest(BaseModel):
    # ... existing fields ...

    # Memory feature fields
    user_id: str | None = None  # UUID from client
    enable_memory: bool = False  # Defaults to False (API default)
```

### FR-2: Memory Context Injection

When `enable_memory=True` and `user_id` is provided:

1. **Before processing:** Call memory service to get relevant memories
2. **Inject into prompt:** Prepend memory context to the user's message

**Memory Context Format:**
```
______ Notice ______
This is not part of what the user has prompted. The app the user uses here has a memory feature enabled so that the user can mention things where the app would normally not have sufficient context, but due to the memory this app wants the mechanism to able to automatically reference things from past sessions/chats, so this is what we identified to be potentially relevant from past chat:
<memory-references>
- [mem_abc123] User has a dog named Max (golden retriever)
- [mem_def456] User prefers short, classic pet names
</memory-references>
____________________

{ORIGINAL_USER_MESSAGE}
```

### FR-3: Memory Extraction After Response

After SSE stream completes (or after non-streaming response):

1. **Fire-and-forget call** to memory extraction API
2. Pass full conversation (all messages + assistant response)
3. Don't block the response - use asyncio background task

```python
async def _extract_memories_background(
    user_id: str,
    conversation: list[dict],
    memory_service_url: str,
) -> None:
    """Background task to extract memories after response."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{memory_service_url}/memories/extract",
                json={
                    "user_id": user_id,
                    "conversation": conversation,
                },
                timeout=30.0,
            )
    except Exception as exc:
        logger.warning("memory_extraction_failed", error=str(exc))
```

### FR-4: Configuration

Add to settings:

```python
# Memory service configuration
memory_service_url: str = Field(
    default="https://janus-memory-service.onrender.com",
    description="URL of the memory service"
)
enable_memory_feature: bool = Field(
    default=True,
    description="Whether memory feature is enabled server-side"
)
memory_timeout_seconds: float = Field(
    default=5.0,
    description="Timeout for memory service calls"
)
```

---

## Technical Requirements

### TR-1: baseline-agent-cli Changes

**Files to Modify:**

1. **`models.py`** - Add `user_id` and `enable_memory` to request model
2. **`config.py`** - Add memory service configuration
3. **`main.py`** - Integrate memory fetch/injection/extraction
4. **`services/__init__.py`** - Export new memory service
5. **NEW: `services/memory.py`** - Memory service client

**main.py Changes:**

```python
from janus_baseline_agent_cli.services.memory import MemoryService

async def stream_response(
    request: ChatCompletionRequest,
    complexity_detector: ComplexityDetector,
    llm_service: LLMService,
    sandy_service: SandyService,
    memory_service: MemoryService,  # NEW
) -> AsyncGenerator[str, None]:
    """Generate streaming response based on complexity."""

    # Memory context injection
    memory_context = ""
    if request.enable_memory and request.user_id:
        memory_context = await memory_service.get_memory_context(
            user_id=request.user_id,
            prompt=_extract_last_user_message(request.messages),
        )

    # Inject memory context into messages
    if memory_context:
        request = _inject_memory_context(request, memory_context)

    # ... existing complexity check and routing ...

    # Collect full response for memory extraction
    full_response = ""

    if settings.always_use_agent or (is_complex and sandy_service.is_available):
        async for chunk in sandy_service.execute_complex(request):
            full_response += _extract_content(chunk)
            yield f"data: {chunk.model_dump_json()}\n\n"
    else:
        async for chunk in llm_service.stream(request):
            full_response += _extract_content(chunk)
            yield f"data: {chunk.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"

    # Fire-and-forget memory extraction
    if request.enable_memory and request.user_id:
        asyncio.create_task(
            memory_service.extract_memories(
                user_id=request.user_id,
                conversation=_build_conversation(request.messages, full_response),
            )
        )
```

### TR-2: baseline-langchain Changes

**Files to Modify:**

1. **`models.py`** - Add `user_id` and `enable_memory` to request model
2. **`config.py`** - Add memory service configuration
3. **`main.py`** - Integrate memory fetch/injection/extraction
4. **NEW: `services/memory.py`** - Memory service client (can be shared or duplicated)

**main.py Changes:**

Similar pattern to baseline-agent-cli but adapted to LangChain's agent streaming.

### TR-3: Memory Service Client

**`services/memory.py`:**

```python
"""Memory service client for fetching and extracting memories."""

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class MemoryReference(BaseModel):
    id: str
    caption: str


class MemoryService:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_relevant_memories(
        self,
        user_id: str,
        prompt: str,
    ) -> list[MemoryReference]:
        """Fetch memories relevant to the user's prompt."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/memories/relevant",
                    params={"user_id": user_id, "prompt": prompt},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return [
                    MemoryReference(**m) for m in data.get("memories", [])
                ]
        except Exception as exc:
            logger.warning(
                "memory_fetch_failed",
                user_id=user_id,
                error=str(exc),
            )
            return []

    async def get_memory_context(
        self,
        user_id: str,
        prompt: str,
    ) -> str:
        """Get formatted memory context for injection into prompt."""
        memories = await self.get_relevant_memories(user_id, prompt)
        if not memories:
            return ""

        memory_lines = [
            f"- [{m.id}] {m.caption}" for m in memories
        ]

        return f"""______ Notice ______
This is not part of what the user has prompted. The app the user uses here has a memory feature enabled so that the user can mention things where the app would normally not have sufficient context, but due to the memory this app wants the mechanism to able to automatically reference things from past sessions/chats, so this is what we identified to be potentially relevant from past chat:
<memory-references>
{chr(10).join(memory_lines)}
</memory-references>
____________________

"""

    async def extract_memories(
        self,
        user_id: str,
        conversation: list[dict],
    ) -> None:
        """Extract and save memories from conversation (fire-and-forget)."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/memories/extract",
                    json={
                        "user_id": user_id,
                        "conversation": conversation,
                    },
                    timeout=30.0,  # Longer timeout for extraction
                )
                logger.info(
                    "memory_extraction_sent",
                    user_id=user_id,
                    message_count=len(conversation),
                )
        except Exception as exc:
            logger.warning(
                "memory_extraction_failed",
                user_id=user_id,
                error=str(exc),
            )
```

---

## Files to Modify

### baseline-agent-cli

| File | Changes |
|------|---------|
| `janus_baseline_agent_cli/models.py` | Add `user_id`, `enable_memory` fields |
| `janus_baseline_agent_cli/config.py` | Add memory service settings |
| `janus_baseline_agent_cli/main.py` | Integrate memory flow |
| `janus_baseline_agent_cli/services/__init__.py` | Export MemoryService |
| `janus_baseline_agent_cli/services/memory.py` | NEW: Memory service client |

### baseline-langchain

| File | Changes |
|------|---------|
| `janus_baseline_langchain/models.py` | Add `user_id`, `enable_memory` fields |
| `janus_baseline_langchain/config.py` | Add memory service settings |
| `janus_baseline_langchain/main.py` | Integrate memory flow |
| `janus_baseline_langchain/services/__init__.py` | Export MemoryService |
| `janus_baseline_langchain/services/memory.py` | NEW: Memory service client |

---

## Deployment Steps

1. Ensure Spec 72 (Memory Service Backend) is deployed
2. Add `MEMORY_SERVICE_URL` to baseline environment variables on Render
3. Deploy updated baselines
4. Test memory flow end-to-end

---

## Acceptance Criteria

- [ ] Both baselines accept `user_id` and `enable_memory` in requests
- [ ] Relevant memories are fetched before processing (when enabled)
- [ ] Memory context is correctly injected into prompts
- [ ] Memory extraction runs after response completes
- [ ] Memory feature gracefully degrades if service unavailable
- [ ] No impact on response latency when memory disabled
- [ ] Background tasks don't block main response

---

## Testing Checklist

- [ ] Unit tests for memory service client
- [ ] Test memory context formatting
- [ ] Test with memory enabled + no memories → no context injected
- [ ] Test with memory enabled + memories → context injected
- [ ] Test with memory disabled → no service calls
- [ ] Test memory extraction fires after streaming completes
- [ ] Test graceful degradation when memory service down
- [ ] Integration test: full flow with UI

---

## Notes

- Memory service calls should NEVER block or slow down the main response
- If memory service is unavailable, continue without memories
- The memory context is injected into the LAST user message (not as a separate message)
- Extraction happens in background after `[DONE]` is sent
