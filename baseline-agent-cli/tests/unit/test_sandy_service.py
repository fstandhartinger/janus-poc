"""Unit tests for Sandy service helpers."""

import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import (
    ChatCompletionRequest,
    GenerationFlags,
    Message,
    MessageRole,
)
from janus_baseline_agent_cli.services.sandy import SandyService


def test_extract_task_text_content() -> None:
    service = SandyService(Settings())
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Write hello world")],
    )
    task = service._extract_task(request)
    assert "hello world" in task.lower()


def test_extract_task_multimodal_content() -> None:
    service = SandyService(Settings())
    request = ChatCompletionRequest(
        model="baseline",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "text", "text": "Analyze this"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                ],
            )
        ],
    )
    task = service._extract_task(request)
    assert "Analyze this" in task
    assert "image" in task.lower()


# ─── Generation-flag intent inference ────────────────────────────────────────
#
# Without these inferences, plain prompts like "create an image of a cute cat"
# go to the agent path *without* the "You MUST generate …" wrapper, and the
# tool-poor models behind https://claude.chutes.ai respond with a Python code
# block instead of invoking Bash. These tests lock in the heuristic that
# turns natural-language intent into the same generation_flags the UI's plus
# menu would set explicitly.


@pytest.mark.parametrize(
    "text,expected_image,expected_video,expected_audio",
    [
        ("create an image of a cute cat", True, False, False),
        ("Create An Image of a sunset over the alps", True, False, False),
        ("generate an image of a futuristic city", True, False, False),
        ("draw a robot holding a flower", True, False, False),
        ("draw me something cool", True, False, False),
        ("make a picture of my dog", True, False, False),
        ("erstelle bild von einem hund", True, False, False),
        ("make a video of a dog running", False, True, False),
        ("animate this story for me", False, True, False),
        ("read this aloud please", False, False, True),
        ("text to speech: hello world", False, False, True),
        ("generate audio narration of this paragraph", False, False, True),
    ],
)
def test_infer_generation_flags_recognises_natural_intent(
    text: str, expected_image: bool, expected_video: bool, expected_audio: bool
) -> None:
    flags = SandyService._infer_generation_flags(text)
    assert flags is not None, f"expected to infer flags from {text!r}"
    assert flags.generate_image is expected_image
    assert flags.generate_video is expected_video
    assert flags.generate_audio is expected_audio


@pytest.mark.parametrize(
    "text",
    [
        "explain why the sky is blue",
        "what is rayleigh scattering",
        "how do images get compressed in jpeg",
        "summarise this article",
        "",
        "   ",
    ],
)
def test_infer_generation_flags_does_not_false_positive(text: str) -> None:
    assert SandyService._infer_generation_flags(text) is None


def test_build_agent_prompt_auto_wraps_image_request() -> None:
    """An image-style prompt with no explicit flags should still pick up the
    'You MUST generate one or more images …' wrapper from the inferred
    generation_flags. This is the regression guard for the janus.rodeo
    'create an image of a cute cat' bug (2026-04-16)."""
    service = SandyService(Settings())
    wrapped = service._build_agent_prompt("create an image of a cute cat", None)
    assert "MUST generate one or more images" in wrapped
    assert "create an image of a cute cat" in wrapped


def test_build_agent_prompt_respects_explicit_flags() -> None:
    service = SandyService(Settings())
    flags = GenerationFlags(generate_audio=True)
    wrapped = service._build_agent_prompt("read this", flags)
    assert "AUDIO GENERATION" in wrapped
    assert "IMAGE GENERATION" not in wrapped


def test_build_agent_prompt_passes_through_plain_chitchat() -> None:
    service = SandyService(Settings())
    wrapped = service._build_agent_prompt("how does rayleigh scattering work", None)
    assert "Generation Instructions" not in wrapped
    assert wrapped == "how does rayleigh scattering work"
