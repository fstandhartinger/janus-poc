# Spec 38: Multimodal Vision Model Support

## Status: COMPLETE

## Context / Why

When users attach images to their messages, the baseline implementations currently use the same text-only LLM model, which cannot "see" the images. To properly handle image-based queries (e.g., "What's in this image?", "Explain this diagram"), the baselines must:

1. Detect when messages contain images
2. Route to a vision-capable model
3. Format the request properly for multimodal processing

Chutes provides several vision-capable models that can process images alongside text.

## Goals

- Detect image content in user messages
- Route image-containing requests to vision models
- Support primary model with fallback
- Maintain streaming compatibility
- Update both agent-cli and langchain baselines

## Non-Goals

- Image generation (handled by separate endpoints)
- Video understanding
- Real-time image processing
- Training or fine-tuning vision models

## Functional Requirements

### FR-1: Vision Model Configuration

```python
# baseline-agent-cli/janus_baseline_agent_cli/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Vision Models (for image understanding)
    vision_model_primary: str = "Qwen/Qwen3-VL-235B-A22B-Instruct"
    vision_model_fallback: str = "chutesai/Mistral-Small-3.2-24B-Instruct-2506"
    vision_model_timeout: float = 60.0  # Vision models may be slower

    # Vision detection
    enable_vision_routing: bool = True

    class Config:
        env_prefix = "BASELINE_"
```

### FR-2: Image Content Detection

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/vision.py

from typing import Union
from janus_baseline_agent_cli.models.openai import (
    Message,
    MessageContent,
    ImageUrlContent,
)


def contains_images(messages: list[Message]) -> bool:
    """Check if any message contains image content."""
    for message in messages:
        if has_image_content(message.content):
            return True
    return False


def has_image_content(content: Union[str, list, None]) -> bool:
    """Check if message content contains images."""
    if content is None or isinstance(content, str):
        return False

    for part in content:
        # Handle dict format
        if isinstance(part, dict):
            if part.get('type') == 'image_url':
                return True
        # Handle Pydantic model
        elif isinstance(part, ImageUrlContent):
            return True

    return False


def count_images(messages: list[Message]) -> int:
    """Count total images across all messages."""
    count = 0
    for message in messages:
        if message.content and not isinstance(message.content, str):
            for part in message.content:
                if isinstance(part, dict) and part.get('type') == 'image_url':
                    count += 1
                elif isinstance(part, ImageUrlContent):
                    count += 1
    return count


def get_image_urls(message: Message) -> list[str]:
    """Extract image URLs from a message."""
    urls = []
    if message.content and not isinstance(message.content, str):
        for part in message.content:
            if isinstance(part, dict) and part.get('type') == 'image_url':
                url = part.get('image_url', {}).get('url', '')
                if url:
                    urls.append(url)
            elif isinstance(part, ImageUrlContent):
                urls.append(part.image_url.url)
    return urls
```

### FR-3: Vision-Aware LLM Service

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/llm.py

import logging
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from janus_baseline_agent_cli.config import get_settings
from janus_baseline_agent_cli.models.openai import (
    ChatCompletionRequest,
    ChatCompletionChunk,
)
from janus_baseline_agent_cli.services.vision import contains_images

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service with vision model routing."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.default_model = settings.model
        self.vision_model_primary = settings.vision_model_primary
        self.vision_model_fallback = settings.vision_model_fallback
        self.vision_timeout = settings.vision_model_timeout
        self.enable_vision_routing = settings.enable_vision_routing

    def select_model(self, request: ChatCompletionRequest) -> str:
        """Select appropriate model based on message content."""
        if not self.enable_vision_routing:
            return request.model or self.default_model

        # Check for images in the conversation
        if contains_images(request.messages):
            logger.info(
                "Images detected in messages, routing to vision model: %s",
                self.vision_model_primary
            )
            return self.vision_model_primary

        return request.model or self.default_model

    async def stream_completion(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream completion with automatic vision model routing."""
        model = self.select_model(request)
        is_vision = model in (self.vision_model_primary, self.vision_model_fallback)

        # Prepare messages for API
        messages = [
            {"role": m.role.value, "content": self._format_content(m.content)}
            for m in request.messages
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens,
                timeout=self.vision_timeout if is_vision else 30.0,
            )

            async for chunk in stream:
                yield ChatCompletionChunk(
                    id=chunk.id,
                    object="chat.completion.chunk",
                    created=chunk.created,
                    model=chunk.model,
                    choices=[
                        {
                            "index": c.index,
                            "delta": {
                                "role": c.delta.role,
                                "content": c.delta.content,
                            },
                            "finish_reason": c.finish_reason,
                        }
                        for c in chunk.choices
                    ],
                )

        except Exception as e:
            # Try fallback for vision requests
            if is_vision and model == self.vision_model_primary:
                logger.warning(
                    "Primary vision model failed, trying fallback: %s",
                    self.vision_model_fallback
                )
                async for chunk in self._stream_with_fallback(request, messages):
                    yield chunk
            else:
                raise

    async def _stream_with_fallback(
        self,
        request: ChatCompletionRequest,
        messages: list[dict],
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Stream with fallback vision model."""
        stream = await self.client.chat.completions.create(
            model=self.vision_model_fallback,
            messages=messages,
            stream=True,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
            timeout=self.vision_timeout,
        )

        async for chunk in stream:
            yield ChatCompletionChunk(
                id=chunk.id,
                object="chat.completion.chunk",
                created=chunk.created,
                model=chunk.model,
                choices=[
                    {
                        "index": c.index,
                        "delta": {
                            "role": c.delta.role,
                            "content": c.delta.content,
                        },
                        "finish_reason": c.finish_reason,
                    }
                    for c in chunk.choices
                ],
            )

    def _format_content(self, content) -> str | list:
        """Format content for API request."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content

        # Convert to API format
        formatted = []
        for part in content:
            if isinstance(part, dict):
                formatted.append(part)
            elif hasattr(part, 'model_dump'):
                formatted.append(part.model_dump())
            else:
                formatted.append({"type": "text", "text": str(part)})

        return formatted
```

### FR-4: Update Complexity Detection

Images should influence complexity routing:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/complexity.py

from janus_baseline_agent_cli.services.vision import contains_images, count_images


@dataclass(frozen=True)
class ComplexityAnalysis:
    is_complex: bool
    reason: str
    keywords_matched: list[str]
    multimodal_detected: bool
    has_images: bool  # NEW: Track if images are present
    image_count: int  # NEW: Number of images
    text_preview: str


class ComplexityDetector:
    """Detect request complexity with image awareness."""

    def analyze(self, request: ChatCompletionRequest) -> ComplexityAnalysis:
        """Analyze request complexity."""
        messages = request.messages

        # Check for images
        has_images = contains_images(messages)
        image_count = count_images(messages) if has_images else 0

        # Extract text for keyword analysis
        text = self._extract_text(messages)
        text_preview = text[:100] if text else ""

        # Keyword detection
        keywords_matched = self._find_keywords(text)

        # Multimodal generation detection (creating images, not understanding)
        multimodal_detected = self._detect_multimodal_generation(text)

        # Determine complexity
        # Note: Image understanding alone doesn't require agent
        # but image + complex task (e.g., "analyze this code screenshot") might
        is_complex = False
        reason = "simple"

        if multimodal_detected:
            is_complex = True
            reason = "multimodal_generation"
        elif keywords_matched:
            is_complex = True
            reason = "complex_keywords"
        elif has_images and self._needs_agent_for_images(text):
            # Only complex if image analysis requires tools
            is_complex = True
            reason = "image_with_tools"

        return ComplexityAnalysis(
            is_complex=is_complex,
            reason=reason,
            keywords_matched=keywords_matched,
            multimodal_detected=multimodal_detected,
            has_images=has_images,
            image_count=image_count,
            text_preview=text_preview,
        )

    def _needs_agent_for_images(self, text: str) -> bool:
        """Check if image task needs agent (tools beyond vision)."""
        # Phrases that suggest need for code execution or search
        agent_triggers = [
            "search for", "find more", "look up",
            "write code", "execute", "run this",
            "compare with", "fetch", "download",
        ]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in agent_triggers)
```

### FR-5: Vision Support in Sandy Agent

When routing to Sandy, pass image context:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py

from janus_baseline_agent_cli.services.vision import get_image_urls, contains_images


class SandyService:
    """Sandy sandbox service with image support."""

    def _extract_task(self, request: ChatCompletionRequest) -> str:
        """Extract task from last user message, including image references."""
        for msg in reversed(request.messages):
            if msg.role.value == "user" and msg.content:
                task_text = ""
                image_urls = []

                if isinstance(msg.content, str):
                    task_text = msg.content
                else:
                    for part in msg.content:
                        if hasattr(part, 'text'):
                            task_text = part.text
                            break
                        elif isinstance(part, dict):
                            if part.get('type') == 'text':
                                task_text = part.get('text', '')
                            elif part.get('type') == 'image_url':
                                url = part.get('image_url', {}).get('url', '')
                                if url:
                                    image_urls.append(url)

                # Append image references to task
                if image_urls:
                    task_text += f"\n\n[{len(image_urls)} image(s) attached - use vision capabilities to analyze]"

                return task_text

        return "No task specified"

    def _build_agent_env(self, request: ChatCompletionRequest) -> dict:
        """Build environment variables for agent, including vision config."""
        settings = get_settings()
        env = {
            # ... existing env vars ...
            "JANUS_VISION_MODEL": settings.vision_model_primary,
            "JANUS_VISION_FALLBACK": settings.vision_model_fallback,
            "JANUS_HAS_IMAGES": str(contains_images(request.messages)).lower(),
        }
        return env
```

### FR-6: LangChain Baseline Vision Support

```python
# baseline-langchain/janus_baseline_langchain/services/vision.py

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages.base import BaseMessage

from janus_baseline_langchain.config import get_settings


def create_vision_chain():
    """Create a LangChain chain with vision model."""
    settings = get_settings()

    # Primary vision model
    vision_llm = ChatOpenAI(
        model=settings.vision_model_primary,
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.openai_base_url,
        streaming=True,
        timeout=settings.vision_model_timeout,
    )

    return vision_llm


def convert_to_langchain_messages(messages: list) -> list[BaseMessage]:
    """Convert OpenAI messages to LangChain format, preserving images."""
    lc_messages = []

    for msg in messages:
        role = msg.get('role') or msg.role.value
        content = msg.get('content') or msg.content

        if role == 'user':
            if isinstance(content, str):
                lc_messages.append(HumanMessage(content=content))
            else:
                # Multimodal content
                lc_messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            text = content if isinstance(content, str) else _extract_text(content)
            lc_messages.append(AIMessage(content=text))

    return lc_messages


def _extract_text(content: list) -> str:
    """Extract text from multimodal content."""
    for part in content:
        if isinstance(part, dict) and part.get('type') == 'text':
            return part.get('text', '')
    return ""
```

### FR-7: Agent Pack Vision Documentation

```markdown
# agent-pack/docs/models/vision.md

# Vision Models on Chutes

## Available Models

### Primary: Qwen3-VL-235B-A22B-Instruct
- **Model ID**: `Qwen/Qwen3-VL-235B-A22B-Instruct`
- **Capabilities**: Image understanding, OCR, diagram analysis, visual QA
- **Context**: 32k tokens
- **Best for**: Complex visual reasoning, detailed image analysis

### Fallback: Mistral-Small-3.2-24B-Instruct-2506
- **Model ID**: `chutesai/Mistral-Small-3.2-24B-Instruct-2506`
- **Capabilities**: Basic image understanding, visual QA
- **Context**: 128k tokens
- **Best for**: Simple image questions, faster responses

## Usage

Images are passed as part of the message content array:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,..."
                }
            }
        ]
    }
]
```

## Image Formats Supported

- JPEG, PNG, GIF, WebP
- Base64 data URLs
- HTTP/HTTPS URLs (external images)

## Detail Levels

The `detail` parameter controls image processing:
- `"low"`: 512x512 max, faster processing
- `"high"`: Native resolution, better for OCR/details
- `"auto"` (default): Automatic selection based on image

## Best Practices

1. **Use `low` detail** for simple "what is this?" questions
2. **Use `high` detail** for OCR, reading text, diagrams
3. **Limit image count** - most tasks need only 1-2 images
4. **Compress large images** - base64 adds ~33% overhead
```

## Non-Functional Requirements

### NFR-1: Performance

- Vision model selection adds <10ms latency
- Fallback triggered within 5 seconds of primary failure
- Image content preserved without re-encoding

### NFR-2: Reliability

- Automatic fallback on primary model failure
- Graceful degradation to text-only if no vision models available
- Connection timeouts prevent hanging requests

### NFR-3: Cost Efficiency

- Only route to vision models when images present
- Use detail levels to control processing costs
- Cache model availability checks

## Environment Variables

```bash
# Vision Model Configuration
BASELINE_VISION_MODEL_PRIMARY=Qwen/Qwen3-VL-235B-A22B-Instruct
BASELINE_VISION_MODEL_FALLBACK=chutesai/Mistral-Small-3.2-24B-Instruct-2506
BASELINE_VISION_MODEL_TIMEOUT=60.0
BASELINE_ENABLE_VISION_ROUTING=true
```

## Acceptance Criteria

- [ ] Images in messages detected correctly
- [ ] Vision model selected when images present
- [ ] Fallback works when primary fails
- [ ] Streaming works with vision models
- [ ] Complexity analysis includes image info
- [ ] Agent pack includes vision documentation
- [ ] LangChain baseline supports vision
- [ ] Tests cover image detection and routing

## Files to Modify/Create

```
baseline-agent-cli/
├── janus_baseline_agent_cli/
│   ├── config.py                # MODIFY - Add vision settings
│   └── services/
│       ├── vision.py            # NEW - Vision detection utilities
│       ├── llm.py               # MODIFY - Vision model routing
│       ├── complexity.py        # MODIFY - Image-aware analysis
│       └── sandy.py             # MODIFY - Pass image context
├── agent-pack/
│   └── docs/models/
│       └── vision.md            # NEW - Vision model documentation
└── tests/
    └── test_vision.py           # NEW - Vision routing tests

baseline-langchain/
└── janus_baseline_langchain/
    ├── config.py                # MODIFY - Add vision settings
    └── services/
        └── vision.py            # NEW - LangChain vision support
```

## Open Questions

1. **Image preprocessing**: Should we resize large images before sending?
2. **Model availability**: How to check if vision models are available on Chutes?
3. **Cost tracking**: Should we log vision model usage separately?
4. **Multi-image limits**: What's the maximum images per request?

## Related Specs

- `specs/37_extended_file_attachments.md` - File attachment support
- `specs/30_janus_benchmark_integration.md` - Benchmark suite
- `specs/33_janus_multimodal_benchmark.md` - Multimodal benchmarks

NR_OF_TRIES: 1
