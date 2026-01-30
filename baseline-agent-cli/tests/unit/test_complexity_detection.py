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


def test_simple_factual_query_pattern_detection(detector: ComplexityDetector) -> None:
    """Test that simple factual questions are correctly identified as fast path."""
    simple_queries = [
        "Explain why the sky is blue",
        "What is photosynthesis?",
        "How does gravity work?",
        "Why are leaves green?",
        "What is 2 + 2?",
        "Tell me about the solar system",
        "Can you explain quantum mechanics?",
        "Who was Albert Einstein?",
        "When did World War 2 end?",
    ]

    for query in simple_queries:
        result = detector._is_simple_factual_query(query)
        assert result is True, f"Expected '{query}' to be identified as simple factual query"


def test_complex_queries_not_matched_as_simple(detector: ComplexityDetector) -> None:
    """Test that complex queries are NOT matched as simple factual."""
    complex_queries = [
        "Write a Python script to download this file",
        "Search the web for the latest news about AI",
        "Generate an image of a sunset",
        "Run the tests and fix any errors",
        "Open the browser and take a screenshot of google.com",
    ]

    for query in complex_queries:
        result = detector._is_simple_factual_query(query)
        assert result is False, f"Expected '{query}' to NOT be identified as simple factual query"
