"""Tests for complexity detection."""

import pytest

from janus_baseline.models import Message, MessageRole
from janus_baseline.services import ComplexityDetector
from janus_baseline.config import Settings


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
