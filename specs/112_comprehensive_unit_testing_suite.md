# Spec 100: Comprehensive Unit Testing Suite

## Status: COMPLETE

**Priority:** High
**Complexity:** High
**Prerequisites:** All previous specs complete

---

## Overview

This spec defines comprehensive unit tests for all Janus components to ensure individual functions, classes, and modules work correctly in isolation. Unit tests should run fast, be deterministic, and cover edge cases.

**Important:** If any tests fail during implementation, FIX the underlying code to make them pass. Tests are a specification of expected behavior.

---

## Testing Philosophy

1. **Tests are specifications** - If a test fails, the code is wrong (unless the spec changed)
2. **Fix, don't skip** - Never skip failing tests; fix the underlying issue
3. **High coverage** - Aim for >80% line coverage on critical paths
4. **Fast execution** - Unit tests should complete in <30 seconds total
5. **No external dependencies** - Mock all external APIs, databases, file systems

---

## Part 1: Gateway Unit Tests

### Location: `gateway/tests/unit/`

### Test File: `test_models.py`

```python
import pytest
from janus_gateway.models.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    MessageRole,
    TextContent,
    ImageUrlContent,
    Usage,
)

class TestChatCompletionRequest:
    """Test OpenAI-compatible request model validation."""

    def test_minimal_valid_request(self):
        """Minimal request with just model and messages."""
        request = ChatCompletionRequest(
            model="baseline-cli-agent",
            messages=[Message(role=MessageRole.USER, content="Hello")]
        )
        assert request.model == "baseline-cli-agent"
        assert len(request.messages) == 1
        assert request.stream is True  # Default

    def test_request_with_all_optional_fields(self):
        """Request with all optional fields populated."""
        request = ChatCompletionRequest(
            model="baseline-cli-agent",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            stream=False,
            user="user-123",
            metadata={"session": "abc"},
        )
        assert request.temperature == 0.7
        assert request.stream is False

    def test_text_only_message(self):
        """Message with string content."""
        msg = Message(role=MessageRole.USER, content="Hello world")
        assert msg.content == "Hello world"

    def test_multimodal_message_with_image(self):
        """Message with text + image content parts."""
        request = ChatCompletionRequest(
            model="baseline-cli-agent",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content=[
                        {"type": "text", "text": "What's in this image?"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}}
                    ]
                )
            ]
        )
        assert isinstance(request.messages[0].content, list)
        assert len(request.messages[0].content) == 2

    def test_system_message(self):
        """System message role is accepted."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful."),
                Message(role=MessageRole.USER, content="Hello"),
            ]
        )
        assert request.messages[0].role == MessageRole.SYSTEM

    def test_assistant_message(self):
        """Assistant message in history."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(role=MessageRole.USER, content="Hi"),
                Message(role=MessageRole.ASSISTANT, content="Hello!"),
                Message(role=MessageRole.USER, content="How are you?"),
            ]
        )
        assert request.messages[1].role == MessageRole.ASSISTANT

    def test_tool_message(self):
        """Tool result message."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(role=MessageRole.USER, content="What's 2+2?"),
                Message(role=MessageRole.TOOL, content="4", tool_call_id="call_123"),
            ]
        )
        assert request.messages[1].role == MessageRole.TOOL

    def test_invalid_empty_messages_rejected(self):
        """Empty messages array should fail validation."""
        with pytest.raises(ValueError):
            ChatCompletionRequest(model="baseline", messages=[])

    def test_temperature_bounds(self):
        """Temperature should be between 0 and 2."""
        # Valid
        ChatCompletionRequest(
            model="baseline",
            messages=[Message(role=MessageRole.USER, content="Hi")],
            temperature=0.0
        )
        ChatCompletionRequest(
            model="baseline",
            messages=[Message(role=MessageRole.USER, content="Hi")],
            temperature=2.0
        )
        # Invalid
        with pytest.raises(ValueError):
            ChatCompletionRequest(
                model="baseline",
                messages=[Message(role=MessageRole.USER, content="Hi")],
                temperature=-0.1
            )

    def test_unicode_content_handling(self):
        """Unicode content is preserved."""
        request = ChatCompletionRequest(
            model="baseline",
            messages=[Message(role=MessageRole.USER, content="Hello world!")]
        )
        assert "" in request.messages[0].content


class TestChatCompletionResponse:
    """Test response model serialization."""

    def test_response_structure(self):
        """Response has correct structure."""
        response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1234567890,
            model="baseline-cli-agent",
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
        assert response.id.startswith("chatcmpl-")
        assert len(response.choices) == 1

    def test_response_with_artifacts(self):
        """Response can include Janus artifacts extension."""
        response = ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=1234567890,
            model="baseline",
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Here's your image:",
                        "artifacts": [
                            {
                                "type": "image",
                                "url": "https://example.com/image.png",
                                "title": "Generated Image",
                            }
                        ]
                    },
                    "finish_reason": "stop",
                }
            ],
        )
        assert response.choices[0]["message"]["artifacts"][0]["type"] == "image"
```

### Test File: `test_streaming.py`

```python
import pytest
import json
from janus_gateway.services.streaming import (
    format_sse_chunk,
    parse_sse_line,
    StreamChunk,
    create_done_marker,
    create_keep_alive,
)

class TestSSEFormatting:
    """Test SSE chunk formatting."""

    def test_format_content_chunk(self):
        """Format a content delta chunk."""
        chunk = StreamChunk(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="baseline",
            choices=[{"index": 0, "delta": {"content": "Hello"}}],
        )
        sse = format_sse_chunk(chunk)
        assert sse.startswith("data: ")
        assert "Hello" in sse
        assert sse.endswith("\n\n")

    def test_format_reasoning_chunk(self):
        """Format a reasoning_content delta chunk."""
        chunk = StreamChunk(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="baseline",
            choices=[{"index": 0, "delta": {"reasoning_content": "Thinking..."}}],
        )
        sse = format_sse_chunk(chunk)
        assert "reasoning_content" in sse

    def test_done_marker(self):
        """[DONE] marker format."""
        done = create_done_marker()
        assert done == "data: [DONE]\n\n"

    def test_keep_alive_format(self):
        """Keep-alive is SSE comment."""
        ka = create_keep_alive()
        assert ka == ": ping\n\n"

    def test_parse_sse_line_data(self):
        """Parse data line."""
        line = 'data: {"id": "123"}'
        result = parse_sse_line(line)
        assert result["type"] == "data"
        assert result["content"]["id"] == "123"

    def test_parse_sse_line_done(self):
        """Parse [DONE] marker."""
        line = "data: [DONE]"
        result = parse_sse_line(line)
        assert result["type"] == "done"

    def test_parse_sse_line_comment(self):
        """Parse comment/keep-alive."""
        line = ": ping"
        result = parse_sse_line(line)
        assert result["type"] == "comment"


class TestStreamChunkValidation:
    """Test stream chunk model."""

    def test_chunk_with_finish_reason(self):
        """Final chunk has finish_reason."""
        chunk = StreamChunk(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="baseline",
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
        )
        assert chunk.choices[0]["finish_reason"] == "stop"

    def test_chunk_with_usage(self):
        """Chunk can include usage stats."""
        chunk = StreamChunk(
            id="chatcmpl-123",
            object="chat.completion.chunk",
            created=1234567890,
            model="baseline",
            choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        assert chunk.usage["total_tokens"] == 30
```

### Test File: `test_competitor_registry.py`

```python
import pytest
from janus_gateway.services.competitor_registry import (
    CompetitorRegistry,
    Competitor,
    CompetitorStatus,
)

class TestCompetitorRegistry:
    """Test competitor registration and selection."""

    @pytest.fixture
    def registry(self):
        return CompetitorRegistry()

    def test_register_competitor(self, registry):
        """Register a new competitor."""
        comp = Competitor(
            id="baseline-cli-agent",
            name="Baseline CLI Agent",
            url="http://localhost:8001",
            status=CompetitorStatus.ACTIVE,
        )
        registry.register(comp)
        assert "baseline-cli-agent" in registry.list()

    def test_get_competitor_by_id(self, registry):
        """Get competitor by ID."""
        comp = Competitor(
            id="test-competitor",
            name="Test",
            url="http://localhost:9999",
        )
        registry.register(comp)
        result = registry.get("test-competitor")
        assert result.url == "http://localhost:9999"

    def test_get_default_competitor(self, registry):
        """Get default competitor when model not specified."""
        comp = Competitor(
            id="baseline-cli-agent",
            name="Baseline",
            url="http://localhost:8001",
            is_default=True,
        )
        registry.register(comp)
        result = registry.get_default()
        assert result.id == "baseline-cli-agent"

    def test_unknown_competitor_raises(self, registry):
        """Unknown competitor ID raises error."""
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_list_active_only(self, registry):
        """List filters to active competitors."""
        registry.register(Competitor(id="active", name="A", url="http://a", status=CompetitorStatus.ACTIVE))
        registry.register(Competitor(id="inactive", name="B", url="http://b", status=CompetitorStatus.INACTIVE))
        active = registry.list(active_only=True)
        assert "active" in active
        assert "inactive" not in active
```

### Test File: `test_transcription.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from janus_gateway.routers.transcription import transcribe_audio, TranscriptionRequest

class TestTranscription:
    """Test transcription proxy."""

    @pytest.mark.asyncio
    async def test_transcription_request_format(self):
        """Request includes audio_b64 and optional language."""
        req = TranscriptionRequest(
            audio_b64="SGVsbG8gV29ybGQ=",
            language="en"
        )
        assert len(req.audio_b64) > 0
        assert req.language == "en"

    @pytest.mark.asyncio
    async def test_transcription_auto_language(self):
        """Language can be None for auto-detection."""
        req = TranscriptionRequest(audio_b64="SGVsbG8=")
        assert req.language is None

    @pytest.mark.asyncio
    @patch("janus_gateway.routers.transcription.httpx.AsyncClient")
    async def test_transcription_success(self, mock_client):
        """Successful transcription returns text."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hello world", "language": "en"}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        # Test would call the actual endpoint
        # This is a pattern test - actual implementation may vary
        pass
```

---

## Part 2: Baseline Agent CLI Unit Tests

### Location: `baseline-agent-cli/tests/unit/`

### Test File: `test_complexity_detection.py`

```python
import pytest
from janus_baseline_agent_cli.services.complexity import (
    ComplexityDetector,
    ComplexityAnalysis,
)
from janus_baseline_agent_cli.models.openai import Message, MessageRole

class TestComplexityDetector:
    """Test complexity detection logic."""

    @pytest.fixture
    def detector(self):
        return ComplexityDetector()

    # Simple queries - should NOT trigger agent
    @pytest.mark.parametrize("prompt", [
        "What is 2+2?",
        "Hello, how are you?",
        "What's the capital of France?",
        "Tell me a joke",
        "Explain quantum computing",
        "What time is it?",
        "Who is the president?",
        "Define photosynthesis",
    ])
    def test_simple_queries_not_complex(self, detector, prompt):
        """Simple factual queries use fast path."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        result = detector.analyze(messages)
        assert result.is_complex is False, f"'{prompt}' should be simple"

    # Complex queries - SHOULD trigger agent
    @pytest.mark.parametrize("prompt,reason", [
        ("Write a Python function to sort a list", "code"),
        ("Generate an image of a cat", "image"),
        ("Create a video of a sunset", "video"),
        ("Search the web for latest news", "search"),
        ("Convert this text to speech", "tts"),
        ("Make me a music clip", "audio"),
        ("Create a PowerPoint presentation", "file"),
        ("Build a website for my business", "code"),
        ("Execute this Python code: print(1)", "code"),
        ("Run the tests and show me results", "code"),
        ("Download this file and analyze it", "file"),
    ])
    def test_complex_queries_detected(self, detector, prompt, reason):
        """Complex queries trigger agent path."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        result = detector.analyze(messages)
        assert result.is_complex is True, f"'{prompt}' should be complex ({reason})"

    def test_keyword_matching_case_insensitive(self, detector):
        """Keywords matched regardless of case."""
        messages = [Message(role=MessageRole.USER, content="GENERATE AN IMAGE")]
        result = detector.analyze(messages)
        assert result.is_complex is True

    def test_multimodal_content_detected(self, detector):
        """Images in content trigger complex path."""
        messages = [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}
                ]
            )
        ]
        result = detector.analyze(messages)
        assert result.has_images is True
        # Note: Image understanding alone may not be complex
        # unless combined with tool-requiring keywords

    def test_empty_message_not_complex(self, detector):
        """Empty message is not complex."""
        messages = [Message(role=MessageRole.USER, content="")]
        result = detector.analyze(messages)
        assert result.is_complex is False

    def test_conversation_history_analyzed(self, detector):
        """Full conversation history is considered."""
        messages = [
            Message(role=MessageRole.USER, content="I want to create something"),
            Message(role=MessageRole.ASSISTANT, content="What would you like to create?"),
            Message(role=MessageRole.USER, content="an image of a cat"),
        ]
        result = detector.analyze(messages)
        assert result.is_complex is True

    def test_analysis_returns_text_preview(self, detector):
        """Analysis includes text preview for logging."""
        messages = [Message(role=MessageRole.USER, content="Hello world")]
        result = detector.analyze(messages)
        assert "Hello" in result.text_preview

    def test_matched_keywords_returned(self, detector):
        """Matched keywords are returned for debugging."""
        messages = [Message(role=MessageRole.USER, content="Generate an image")]
        result = detector.analyze(messages)
        assert len(result.keywords_matched) > 0


class TestComplexityEdgeCases:
    """Edge cases for complexity detection."""

    @pytest.fixture
    def detector(self):
        return ComplexityDetector()

    def test_unicode_handling(self, detector):
        """Unicode text doesn't break detection."""
        messages = [Message(role=MessageRole.USER, content="")]
        result = detector.analyze(messages)
        assert isinstance(result, ComplexityAnalysis)

    def test_very_long_message(self, detector):
        """Very long messages are handled."""
        long_text = "Hello " * 10000
        messages = [Message(role=MessageRole.USER, content=long_text)]
        result = detector.analyze(messages)
        assert isinstance(result, ComplexityAnalysis)

    def test_special_characters(self, detector):
        """Special characters handled safely."""
        messages = [Message(role=MessageRole.USER, content="<script>alert('xss')</script>")]
        result = detector.analyze(messages)
        assert isinstance(result, ComplexityAnalysis)
```

### Test File: `test_vision_detection.py`

```python
import pytest
from janus_baseline_agent_cli.services.vision import (
    contains_images,
    count_images,
    get_image_urls,
    has_image_content,
)
from janus_baseline_agent_cli.models.openai import Message, MessageRole

class TestVisionDetection:
    """Test image detection in messages."""

    def test_text_only_no_images(self):
        """Text-only messages have no images."""
        messages = [
            Message(role=MessageRole.USER, content="Hello world")
        ]
        assert contains_images(messages) is False

    def test_content_parts_with_image(self):
        """Detect image in content parts."""
        messages = [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "text", "text": "What's this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}
                ]
            )
        ]
        assert contains_images(messages) is True

    def test_base64_image_detected(self):
        """Detect base64 data URL images."""
        messages = [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}}
                ]
            )
        ]
        assert contains_images(messages) is True

    def test_count_multiple_images(self):
        """Count multiple images across messages."""
        messages = [
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "image_url", "image_url": {"url": "https://a.png"}},
                    {"type": "image_url", "image_url": {"url": "https://b.png"}},
                ]
            ),
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "image_url", "image_url": {"url": "https://c.png"}},
                ]
            )
        ]
        assert count_images(messages) == 3

    def test_get_image_urls(self):
        """Extract all image URLs from message."""
        message = Message(
            role=MessageRole.USER,
            content=[
                {"type": "text", "text": "Compare these:"},
                {"type": "image_url", "image_url": {"url": "https://a.png"}},
                {"type": "image_url", "image_url": {"url": "https://b.png"}},
            ]
        )
        urls = get_image_urls(message)
        assert len(urls) == 2
        assert "https://a.png" in urls
        assert "https://b.png" in urls

    def test_none_content_no_images(self):
        """None content has no images."""
        assert has_image_content(None) is False

    def test_empty_list_no_images(self):
        """Empty list has no images."""
        assert has_image_content([]) is False

    def test_text_part_only_no_images(self):
        """Text parts only has no images."""
        content = [{"type": "text", "text": "Hello"}]
        assert has_image_content(content) is False
```

### Test File: `test_sandy_service.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from janus_baseline_agent_cli.services.sandy import SandyService

class TestSandyService:
    """Test Sandy sandbox integration."""

    @pytest.fixture
    def sandy_service(self):
        return SandyService()

    @pytest.mark.asyncio
    @patch("janus_baseline_agent_cli.services.sandy.httpx.AsyncClient")
    async def test_create_sandbox(self, mock_client, sandy_service):
        """Create a new sandbox."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sandbox_id": "sandbox-123",
            "host": "localhost",
            "port": 8888,
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        # Test pattern - actual test depends on implementation
        pass

    @pytest.mark.asyncio
    async def test_extract_task_text_content(self, sandy_service):
        """Extract task from text content."""
        from janus_baseline_agent_cli.models.openai import (
            ChatCompletionRequest, Message, MessageRole
        )
        request = ChatCompletionRequest(
            model="baseline",
            messages=[Message(role=MessageRole.USER, content="Write hello world")]
        )
        task = sandy_service._extract_task(request)
        assert "hello world" in task.lower()

    @pytest.mark.asyncio
    async def test_extract_task_multimodal_content(self, sandy_service):
        """Extract task from multimodal content."""
        from janus_baseline_agent_cli.models.openai import (
            ChatCompletionRequest, Message, MessageRole
        )
        request = ChatCompletionRequest(
            model="baseline",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content=[
                        {"type": "text", "text": "Analyze this"},
                        {"type": "image_url", "image_url": {"url": "data:..."}}
                    ]
                )
            ]
        )
        task = sandy_service._extract_task(request)
        assert "Analyze this" in task
        assert "image" in task.lower()  # Should mention attached images
```

---

## Part 3: Baseline LangChain Unit Tests

### Location: `baseline-langchain/tests/unit/`

### Test File: `test_tools.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from janus_baseline_langchain.tools.image_gen import image_generation
from janus_baseline_langchain.tools.tts import text_to_speech
from janus_baseline_langchain.tools.web_search import web_search_tool

class TestImageGenerationTool:
    """Test image generation tool."""

    @pytest.mark.asyncio
    @patch("janus_baseline_langchain.tools.image_gen.httpx.AsyncClient")
    async def test_image_generation_returns_url(self, mock_client):
        """Image generation returns URL."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "data": [{"url": "https://example.com/generated.png"}]
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        # Pattern test - actual implementation may vary
        pass

    def test_tool_description(self):
        """Tool has proper description."""
        assert "image" in image_generation.description.lower()


class TestTTSTool:
    """Test text-to-speech tool."""

    @pytest.mark.asyncio
    @patch("janus_baseline_langchain.tools.tts.httpx.AsyncClient")
    async def test_tts_returns_audio_data(self, mock_client):
        """TTS returns base64 audio data."""
        mock_response = AsyncMock()
        mock_response.content = b"audio data"
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        # Pattern test
        pass

    def test_tool_description(self):
        """Tool has proper description."""
        assert "speech" in text_to_speech.description.lower()


class TestWebSearchTool:
    """Test web search tool."""

    def test_tool_exists(self):
        """Web search tool is configured."""
        assert web_search_tool is not None

    def test_tool_description(self):
        """Tool has proper description."""
        assert "search" in web_search_tool.description.lower()
```

### Test File: `test_agent.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from janus_baseline_langchain.agent import create_agent

class TestAgentCreation:
    """Test LangChain agent setup."""

    @patch("janus_baseline_langchain.agent.ChatOpenAI")
    def test_create_agent_with_tools(self, mock_llm):
        """Agent is created with all tools."""
        mock_llm.return_value = MagicMock()

        # Test pattern - verifies agent creation doesn't error
        pass

    def test_system_prompt_content(self):
        """System prompt includes tool descriptions."""
        from janus_baseline_langchain.agent import SYSTEM_PROMPT
        assert "image" in SYSTEM_PROMPT.lower()
        assert "speech" in SYSTEM_PROMPT.lower()
        assert "search" in SYSTEM_PROMPT.lower()
```

---

## Part 4: UI Unit Tests

### Location: `ui/src/__tests__/`

### Test File: `hooks/useChat.test.ts`

```typescript
import { renderHook, act } from '@testing-library/react';
import { useChat } from '@/hooks/useChat';

describe('useChat hook', () => {
  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
  });

  it('adds user message on send', async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[0].content).toBe('Hello');
  });

  it('sets loading state during request', async () => {
    const { result } = renderHook(() => useChat());

    // Mock would be needed for actual test
    // This is a pattern demonstration
  });

  it('handles streaming responses', async () => {
    const { result } = renderHook(() => useChat());
    // Test streaming message assembly
  });

  it('handles errors gracefully', async () => {
    const { result } = renderHook(() => useChat());
    // Test error state
  });
});
```

### Test File: `hooks/useAudioRecorder.test.ts`

```typescript
import { renderHook, act } from '@testing-library/react';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';

// Mock MediaRecorder
const mockMediaRecorder = {
  start: jest.fn(),
  stop: jest.fn(),
  ondataavailable: null as any,
  onstop: null as any,
  state: 'inactive',
};

const mockGetUserMedia = jest.fn();

beforeAll(() => {
  global.MediaRecorder = jest.fn().mockImplementation(() => mockMediaRecorder);
  global.navigator.mediaDevices = {
    getUserMedia: mockGetUserMedia,
  } as any;
});

describe('useAudioRecorder hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: jest.fn() }],
    });
  });

  it('initializes in not recording state', () => {
    const { result } = renderHook(() => useAudioRecorder());
    expect(result.current.isRecording).toBe(false);
  });

  it('requests microphone permission on start', async () => {
    const { result } = renderHook(() => useAudioRecorder());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(mockGetUserMedia).toHaveBeenCalledWith(
      expect.objectContaining({ audio: expect.any(Object) })
    );
  });

  it('handles permission denied error', async () => {
    mockGetUserMedia.mockRejectedValueOnce(new Error('Permission denied'));

    const { result } = renderHook(() => useAudioRecorder());

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.error).toContain('permission');
  });

  it('tracks recording duration', async () => {
    jest.useFakeTimers();
    const { result } = renderHook(() => useAudioRecorder());

    await act(async () => {
      await result.current.startRecording();
    });

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(result.current.duration).toBeGreaterThan(0);
    jest.useRealTimers();
  });

  it('respects max duration limit', async () => {
    jest.useFakeTimers();
    const maxDuration = 10;
    const { result } = renderHook(() => useAudioRecorder({ maxDuration }));

    await act(async () => {
      await result.current.startRecording();
    });

    act(() => {
      jest.advanceTimersByTime((maxDuration + 1) * 1000);
    });

    // Should auto-stop at max duration
    expect(mockMediaRecorder.stop).toHaveBeenCalled();
    jest.useRealTimers();
  });
});
```

### Test File: `lib/api.test.ts`

```typescript
import { sendChatMessage, parseSSELine } from '@/lib/api';

describe('API utilities', () => {
  describe('parseSSELine', () => {
    it('parses data line', () => {
      const line = 'data: {"id":"123","choices":[{"delta":{"content":"Hi"}}]}';
      const result = parseSSELine(line);
      expect(result.type).toBe('data');
      expect(result.data.id).toBe('123');
    });

    it('parses [DONE] marker', () => {
      const line = 'data: [DONE]';
      const result = parseSSELine(line);
      expect(result.type).toBe('done');
    });

    it('parses comment/keep-alive', () => {
      const line = ': ping';
      const result = parseSSELine(line);
      expect(result.type).toBe('comment');
    });

    it('handles malformed JSON gracefully', () => {
      const line = 'data: {invalid json}';
      const result = parseSSELine(line);
      expect(result.type).toBe('error');
    });
  });
});
```

### Test File: `lib/freeChat.test.ts`

```typescript
import {
  readFreeChatState,
  incrementFreeChatCount,
  remainingFreeChats,
  hasFreeChatRemaining,
} from '@/lib/freeChat';

describe('Free chat limit tracking', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with zero count', () => {
    const state = readFreeChatState();
    expect(state.count).toBe(0);
  });

  it('increments count', () => {
    incrementFreeChatCount();
    incrementFreeChatCount();
    const state = readFreeChatState();
    expect(state.count).toBe(2);
  });

  it('returns remaining chats', () => {
    expect(remainingFreeChats()).toBe(5);
    incrementFreeChatCount();
    expect(remainingFreeChats()).toBe(4);
  });

  it('hasFreeChatRemaining returns false after limit', () => {
    for (let i = 0; i < 5; i++) {
      incrementFreeChatCount();
    }
    expect(hasFreeChatRemaining()).toBe(false);
  });

  it('resets count for new day', () => {
    incrementFreeChatCount();
    incrementFreeChatCount();

    // Simulate next day by manipulating stored date
    const stored = JSON.parse(localStorage.getItem('janus_free_chats_v1')!);
    stored.date = '1999-01-01';
    localStorage.setItem('janus_free_chats_v1', JSON.stringify(stored));

    const state = readFreeChatState();
    expect(state.count).toBe(0);
  });
});
```

---

## Running Unit Tests

### Commands

```bash
# Gateway
cd gateway && pytest tests/unit/ -v --tb=short --cov=janus_gateway --cov-report=term-missing

# Baseline CLI
cd baseline-agent-cli && pytest tests/unit/ -v --tb=short --cov=janus_baseline_agent_cli

# Baseline LangChain
cd baseline-langchain && pytest tests/unit/ -v --tb=short --cov=janus_baseline_langchain

# UI
cd ui && npm test -- --coverage --watchAll=false
```

### Combined Script

```bash
#!/bin/bash
# scripts/run-unit-tests.sh

echo "=== Unit Tests ==="
echo ""

failed=0

echo "--- Gateway ---"
cd gateway && pytest tests/unit/ -v --tb=short || failed=1
cd ..

echo ""
echo "--- Baseline CLI ---"
cd baseline-agent-cli && pytest tests/unit/ -v --tb=short || failed=1
cd ..

echo ""
echo "--- Baseline LangChain ---"
cd baseline-langchain && pytest tests/unit/ -v --tb=short || failed=1
cd ..

echo ""
echo "--- UI ---"
cd ui && npm test -- --watchAll=false || failed=1
cd ..

if [ $failed -eq 1 ]; then
    echo ""
    echo "FAILED: Some unit tests failed. Fix them before proceeding."
    exit 1
fi

echo ""
echo "SUCCESS: All unit tests passed."
```

---

## Acceptance Criteria

- [ ] All gateway models validated with unit tests
- [ ] SSE streaming format tested
- [ ] Competitor registry tested
- [ ] Complexity detection tested for simple vs complex queries
- [ ] Vision detection tested for all image formats
- [ ] Sandy service integration points tested
- [ ] LangChain tools have unit tests
- [ ] UI hooks tested (useChat, useAudioRecorder)
- [ ] API utilities tested
- [ ] Free chat tracking tested
- [ ] All tests pass with >80% coverage on critical paths
- [ ] Any failing tests result in code fixes, not skips

---

## Notes

- Use pytest for Python, Jest for TypeScript
- Mock external dependencies (APIs, databases, file systems)
- Tests should be deterministic and fast (<30s total)
- If a test reveals a bug, fix the bug AND keep the test
- Run tests in CI on every commit

NR_OF_TRIES: 1
