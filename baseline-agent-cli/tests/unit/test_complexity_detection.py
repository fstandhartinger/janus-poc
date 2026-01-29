"""Unit tests for complexity detection."""

import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import Message, MessageRole
from janus_baseline_agent_cli.services import ComplexityDetector


@pytest.fixture
def detector() -> ComplexityDetector:
    settings = Settings(complexity_threshold=500)
    return ComplexityDetector(settings)


def test_simple_queries_not_complex(detector: ComplexityDetector) -> None:
    messages = [Message(role=MessageRole.USER, content="Hello, how are you?")]
    result = detector.analyze(messages)
    assert result.is_complex is False


def test_complex_query_detected(detector: ComplexityDetector) -> None:
    messages = [Message(role=MessageRole.USER, content="Write code to sort a list")]
    result = detector.analyze(messages)
    assert result.is_complex is True
    assert result.reason == "complex_keywords"
    assert len(result.keywords_matched) > 0


def test_multimodal_content_detected(detector: ComplexityDetector) -> None:
    messages = [
        Message(
            role=MessageRole.USER,
            content=[
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            ],
        )
    ]
    result = detector.analyze(messages)
    assert result.has_images is True


def test_empty_message_not_complex(detector: ComplexityDetector) -> None:
    messages = [Message(role=MessageRole.USER, content="")]
    result = detector.analyze(messages)
    assert result.is_complex is False


def test_analysis_returns_text_preview(detector: ComplexityDetector) -> None:
    messages = [Message(role=MessageRole.USER, content="Hello world")]
    result = detector.analyze(messages)
    assert "Hello" in result.text_preview
