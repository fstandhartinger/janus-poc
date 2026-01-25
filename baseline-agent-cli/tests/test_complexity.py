"""Tests for complexity detection."""

import httpx
import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import (
    GenerationFlags,
    ImageUrl,
    ImageUrlContent,
    Message,
    MessageRole,
    TextContent,
)
from janus_baseline_agent_cli.services import ComplexityDetector


@pytest.fixture
def detector() -> ComplexityDetector:
    """Create a complexity detector with default settings."""
    settings = Settings(complexity_threshold=100)
    return ComplexityDetector(settings)


def test_simple_greeting(detector: ComplexityDetector) -> None:
    """Test that a simple greeting is not complex."""
    messages = [Message(role=MessageRole.USER, content="Hello!")]
    is_complex, reason = detector.is_complex(messages)
    assert not is_complex
    assert reason == "simple"


def test_simple_question(detector: ComplexityDetector) -> None:
    """Test that a simple question is not complex."""
    messages = [Message(role=MessageRole.USER, content="What is the capital of France?")]
    is_complex, reason = detector.is_complex(messages)
    assert not is_complex
    assert reason == "simple"


def test_code_writing_request(detector: ComplexityDetector) -> None:
    """Test that a code writing request is complex."""
    messages = [Message(role=MessageRole.USER, content="Write code to sort a list")]
    is_complex, reason = detector.is_complex(messages)
    assert is_complex
    assert reason == "complex_keywords"


def test_implementation_request(detector: ComplexityDetector) -> None:
    """Test that an implementation request is complex."""
    messages = [
        Message(role=MessageRole.USER, content="Implement a binary search algorithm")
    ]
    is_complex, reason = detector.is_complex(messages)
    assert is_complex
    assert reason == "complex_keywords"


def test_debug_request(detector: ComplexityDetector) -> None:
    """Test that a debug request is complex."""
    messages = [Message(role=MessageRole.USER, content="Fix the bug in my code")]
    is_complex, reason = detector.is_complex(messages)
    assert is_complex
    assert reason == "complex_keywords"


def test_multimodal_detection(detector: ComplexityDetector) -> None:
    """Test that multimodal and research requests are complex."""
    messages = [Message(role=MessageRole.USER, content="generate an image of a cat")]
    is_complex, reason = detector.is_complex(messages)
    assert is_complex
    assert reason == "multimodal_request"

    messages = [Message(role=MessageRole.USER, content="create a picture of sunset")]
    is_complex, reason = detector.is_complex(messages)
    assert is_complex
    assert reason == "multimodal_request"

    messages = [Message(role=MessageRole.USER, content="text to speech: hello")]
    is_complex, _ = detector.is_complex(messages)
    assert is_complex

    messages = [Message(role=MessageRole.USER, content="search the web for python docs")]
    is_complex, _ = detector.is_complex(messages)
    assert is_complex


def test_image_request_stays_simple(detector: ComplexityDetector) -> None:
    """Image understanding without tool hints should stay on fast path."""
    messages = [
        Message(
            role=MessageRole.USER,
            content=[
                TextContent(text="What's in this image?"),
                ImageUrlContent(image_url=ImageUrl(url="https://example.com/a.png")),
            ],
        )
    ]
    analysis = detector.analyze(messages)
    assert analysis.is_complex is False
    assert analysis.has_images is True
    assert analysis.image_count == 1


def test_image_with_tool_trigger(detector: ComplexityDetector) -> None:
    """Image requests that need tools should be complex."""
    messages = [
        Message(
            role=MessageRole.USER,
            content=[
                TextContent(text="Search for similar photos online"),
                ImageUrlContent(image_url=ImageUrl(url="https://example.com/a.png")),
            ],
        )
    ]
    analysis = detector.analyze(messages)
    assert analysis.is_complex is True
    assert analysis.reason == "image_with_tools"


def test_generation_flags_force_complex(detector: ComplexityDetector) -> None:
    """Generation flags should force agent routing."""
    messages = [Message(role=MessageRole.USER, content="Hello there")]
    flags = GenerationFlags(generate_image=True, web_search=True)
    analysis = detector.analyze(messages, flags)
    assert analysis.is_complex is True
    assert analysis.reason.startswith("generation_flags:")
    assert "image generation requested" in analysis.reason


def test_empty_messages(detector: ComplexityDetector) -> None:
    """Test that empty messages are not complex."""
    is_complex, reason = detector.is_complex([])
    assert not is_complex
    assert reason == "empty_messages"


def test_no_user_message(detector: ComplexityDetector) -> None:
    """Test that no user message is not complex."""
    messages = [Message(role=MessageRole.SYSTEM, content="You are helpful.")]
    is_complex, reason = detector.is_complex(messages)
    assert not is_complex
    assert reason == "no_user_message"


@pytest.mark.asyncio
async def test_llm_routing_catches_multimodal(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM second pass should mark multimodal requests as complex."""
    settings = Settings(openai_api_key="test")
    detector = ComplexityDetector(settings)

    async def fake_llm_check(text: str) -> tuple[bool, str]:
        return True, "needs_image"

    monkeypatch.setattr(detector, "_llm_routing_check", fake_llm_check)

    messages = [Message(role=MessageRole.USER, content="what's the weather like today")]
    result = await detector.analyze_async(messages)
    assert result.is_complex is True
    assert "llm_verification" in result.reason


@pytest.mark.asyncio
async def test_llm_routing_timeout_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeouts during LLM routing should fall back to agent path."""
    settings = Settings(openai_api_key="test")
    detector = ComplexityDetector(settings)

    class TimeoutAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "TimeoutAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(
        "janus_baseline_agent_cli.services.complexity.httpx.AsyncClient",
        TimeoutAsyncClient,
    )

    messages = [Message(role=MessageRole.USER, content="what's the weather like today")]
    result = await detector.analyze_async(messages)
    assert result.is_complex is True
    assert "llm_verification" in result.reason


@pytest.mark.asyncio
async def test_llm_routing_skips_trivial_greeting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trivial greetings should stay on the fast path without LLM routing."""
    settings = Settings(openai_api_key="test")
    detector = ComplexityDetector(settings)

    async def fail_llm_check(text: str) -> tuple[bool, str]:
        raise AssertionError("LLM check should be skipped for greetings")

    monkeypatch.setattr(detector, "_llm_routing_check", fail_llm_check)

    messages = [Message(role=MessageRole.USER, content="Hello!")]
    result = await detector.analyze_async(messages)
    assert result.is_complex is False
    assert result.reason == "simple"
