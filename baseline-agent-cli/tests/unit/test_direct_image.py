"""Regression tests for the direct image generation path.

This path bypasses Sandy/Claude entirely for image-only prompts because
the Anthropic-compatible proxy at https://claude.chutes.ai consistently
fails to surface tool_use blocks (verified 2026-04-16 with MiniMax M2.5,
Kimi K2.5, DeepSeek V3.2). These tests lock in:
- the lead-in stripping that turns "create an image of a cute cat" into
  the prompt actually sent to image.chutes.ai
- the streaming chunk shape (assistant role first, content with markdown
  data: URL last, terminated by finish_reason=stop)
- the failure modes (HTTP error, missing API key) gracefully degrading to
  a user-facing error chunk rather than raising
"""

from __future__ import annotations

import base64

import httpx
import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import Message, MessageRole
from janus_baseline_agent_cli.services import direct_image


@pytest.mark.parametrize(
    "user_message,expected_subject",
    [
        ("create an image of a cute cat", "a cute cat"),
        ("Create an image of a sunset over the alps", "a sunset over the alps"),
        ("generate an image of a futuristic city", "a futuristic city"),
        ("draw me something cool", "something cool"),
        ("draw a robot holding a flower", "robot holding a flower"),
        ("make a picture of my dog", "my dog"),
        ("erstelle bild von einem hund", "einem hund"),
        ("Hey, create an image of a cat", "a cat"),
    ],
)
def test_extract_image_prompt_strips_lead_ins(user_message, expected_subject):
    assert direct_image.extract_image_prompt(user_message) == expected_subject


def test_extract_image_prompt_passthrough_when_no_lead_in():
    text = "a watercolor painting of mount fuji at dawn"
    assert direct_image.extract_image_prompt(text) == text


def test_extract_image_prompt_handles_empty_input():
    assert direct_image.extract_image_prompt("") == ""
    assert direct_image.extract_image_prompt("   ") == ""


@pytest.mark.asyncio
async def test_stream_image_generation_happy_path(monkeypatch):
    """Successful generate_image call should produce a 4-chunk stream:
    role assistant → reasoning prelude → reasoning ready → content + finish."""

    async def fake_generate_image(prompt, *, api_key, **_):
        assert prompt == "a cute cat"
        assert api_key == "test-key"
        return b"\xff\xd8\xff\xe0FAKEJPEG", "image/jpeg"

    monkeypatch.setattr(direct_image, "generate_image", fake_generate_image)
    settings = Settings()
    settings.chutes_api_key = "test-key"

    chunks = [
        c
        async for c in direct_image.stream_image_generation(
            [Message(role=MessageRole.USER, content="create an image of a cute cat")],
            settings=settings,
            completion_id="test-id",
            model_label="baseline-direct-image",
        )
    ]

    assert chunks, "expected at least one chunk"
    assert chunks[0].choices[0].delta.role == MessageRole.ASSISTANT
    assert any(
        "Generating image directly" in (c.choices[0].delta.reasoning_content or "")
        for c in chunks
    )
    assert any("Image ready" in (c.choices[0].delta.reasoning_content or "") for c in chunks)
    final = chunks[-1]
    assert final.choices[0].finish_reason == "stop"
    content = final.choices[0].delta.content or ""
    assert "Here is the image" in content
    expected_b64 = base64.b64encode(b"\xff\xd8\xff\xe0FAKEJPEG").decode("ascii")
    assert f"data:image/jpeg;base64,{expected_b64}" in content
    assert "![a cute cat](data:image/jpeg;base64," in content


@pytest.mark.asyncio
async def test_stream_image_generation_http_error(monkeypatch):
    """A 5xx from image.chutes.ai must surface as a polite error chunk
    that finishes the stream — never raise into the gateway."""

    async def fake_generate_image(prompt, *, api_key, **_):
        request = httpx.Request("POST", "https://image.chutes.ai/generate")
        response = httpx.Response(500, request=request, text="boom")
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr(direct_image, "generate_image", fake_generate_image)
    settings = Settings()
    settings.chutes_api_key = "test-key"

    chunks = [
        c
        async for c in direct_image.stream_image_generation(
            [Message(role=MessageRole.USER, content="create an image of a cat")],
            settings=settings,
            completion_id="test-id",
            model_label="baseline-direct-image",
        )
    ]
    final = chunks[-1]
    assert final.choices[0].finish_reason == "stop"
    assert "image generation failed" in (final.choices[0].delta.content or "")


@pytest.mark.asyncio
async def test_stream_image_generation_missing_api_key(monkeypatch):
    """Missing CHUTES_API_KEY must yield a user-facing error, not raise."""
    settings = Settings()
    settings.chutes_api_key = ""
    settings.openai_api_key = ""

    chunks = [
        c
        async for c in direct_image.stream_image_generation(
            [Message(role=MessageRole.USER, content="create an image of a cat")],
            settings=settings,
            completion_id="test-id",
            model_label="baseline-direct-image",
        )
    ]
    final = chunks[-1]
    assert final.choices[0].finish_reason == "stop"
    assert "isn't available" in (final.choices[0].delta.content or "")
