"""Tests for complexity detection in baseline-langchain."""

import pytest

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.models import GenerationFlags, Message, MessageRole
from janus_baseline_langchain.services import ComplexityDetector


@pytest.fixture
def detector() -> ComplexityDetector:
    settings = Settings(
        openai_api_key=None,
        chutes_api_key=None,
        complexity_threshold=50,
    )
    return ComplexityDetector(settings)


def _message(content: str) -> Message:
    return Message(role=MessageRole.USER, content=content)


def test_complexity_keywords(detector: ComplexityDetector) -> None:
    analysis = detector.analyze([_message("Please write code to parse JSON")])
    assert analysis.is_complex
    assert analysis.reason == "complex_keywords"


def test_complexity_generation_flags(detector: ComplexityDetector) -> None:
    flags = GenerationFlags(generate_image=True)
    analysis = detector.analyze([_message("Hello")], flags)
    assert analysis.is_complex
    assert "generation_flags" in analysis.reason


@pytest.mark.asyncio
async def test_complexity_async_defaults_conservative_no_api_key(
    detector: ComplexityDetector,
) -> None:
    """When LLM check fails due to missing API key, default to complex (conservative)."""
    analysis = await detector.analyze_async([_message("Tell me a joke")])
    # Conservative default: when LLM unavailable, route to agent path for safety
    assert analysis.is_complex
    assert "conservative_default" in analysis.reason


def test_complexity_url_interaction(detector: ComplexityDetector) -> None:
    analysis = detector.analyze([_message("Check https://example.com and verify it")])
    assert analysis.is_complex
    assert analysis.reason == "url_interaction"
