"""Tests for generation flags prompt handling."""

from janus_baseline_langchain.main import _build_agent_prompt, _generation_flags_payload
from janus_baseline_langchain.models import GenerationFlags


def test_generation_flags_payload_requires_true() -> None:
    assert _generation_flags_payload(None) is None
    assert _generation_flags_payload(GenerationFlags()) is None
    payload = _generation_flags_payload(GenerationFlags(generate_image=True))
    assert payload is not None
    assert payload["generate_image"] is True


def test_build_agent_prompt_includes_instructions() -> None:
    flags = GenerationFlags(generate_audio=True, web_search=True)
    prompt = _build_agent_prompt("Hello", flags)
    assert "AUDIO GENERATION" in prompt
    assert "WEB SEARCH" in prompt
    assert prompt.strip().endswith("Hello")
