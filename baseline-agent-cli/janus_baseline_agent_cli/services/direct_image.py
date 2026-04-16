"""Direct image generation against image.chutes.ai.

This sidesteps the agent / Claude Code path entirely for prompts whose only
purpose is to generate an image. Even with `--dangerously-skip-permissions`
(sandy d9c6edd) and the strongest tool-callers on `claude.chutes.ai`
(MiniMax, Kimi K2.5, DeepSeek V3.2), the Anthropic-compatible proxy
consistently fails to surface tool_use blocks back to Claude Code, so any
"create an image of …" request ends up as a markdown code block instead of
an actual image. Calling the image API directly from this service is the
only 100% reliable path for that workflow.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
from typing import AsyncGenerator, Optional

import httpx

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import (
    ChatCompletionChunk,
    ChunkChoice,
    Delta,
    FinishReason,
    Message,
    MessageContent,
)

logger = logging.getLogger(__name__)

CHUTES_IMAGE_ENDPOINT = "https://image.chutes.ai/generate"
DEFAULT_IMAGE_MODEL = "qwen-image"
DEFAULT_IMAGE_SIZE = 1024
DEFAULT_INFERENCE_STEPS = 30
REQUEST_TIMEOUT_SECONDS = 180


# ─── Prompt extraction ──────────────────────────────────────────────────────

_LEAD_INS = (
    "create an image of",
    "create a image of",
    "create an image",
    "create image of",
    "generate an image of",
    "generate a image of",
    "generate an image",
    "generate image of",
    "make an image of",
    "make a image of",
    "make a picture of",
    "draw me",
    "draw a picture of",
    "draw an image of",
    "draw a",
    "draw an",
    "render a",
    "render an",
    "illustrate",
    "paint a",
    "paint an",
    "image of",
    "picture of",
    "illustration of",
    "photo of",
    "erstelle bild von",
    "erzeuge bild von",
    "male ",
    "zeichne ",
)


def extract_image_prompt(user_message: str) -> str:
    """Strip common lead-ins so the actual subject is what reaches the model.

    Falls back to the original message if nothing recognisable is stripped —
    image.chutes.ai handles freeform prompts fine, this is just a quality
    boost for the very common "create an image of X" / "draw me Y" form.
    """
    text = (user_message or "").strip()
    if not text:
        return ""
    lower = text.lower()
    for prefix in _LEAD_INS:
        if lower.startswith(prefix):
            stripped = text[len(prefix) :].lstrip(" ,:;-")
            return stripped or text
    # Also try stripping after a comma if the first clause is the directive,
    # e.g. "Hey, create an image of a cat" → "a cat".
    for prefix in _LEAD_INS:
        idx = lower.find(prefix)
        if idx > 0 and idx < 40:
            tail = text[idx + len(prefix) :].lstrip(" ,:;-")
            if tail:
                return tail
    return text


# ─── HTTP call ──────────────────────────────────────────────────────────────


async def generate_image(
    prompt: str,
    *,
    api_key: str,
    model: str = DEFAULT_IMAGE_MODEL,
    width: int = DEFAULT_IMAGE_SIZE,
    height: int = DEFAULT_IMAGE_SIZE,
    inference_steps: int = DEFAULT_INFERENCE_STEPS,
) -> tuple[bytes, str]:
    """POST the prompt to image.chutes.ai and return (bytes, mime_type)."""
    if not api_key:
        raise RuntimeError("CHUTES_API_KEY not configured for direct image generation")
    payload = {
        "model": model,
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_inference_steps": inference_steps,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(CHUTES_IMAGE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        mime_type = response.headers.get("content-type") or "image/jpeg"
        return response.content, mime_type


# ─── Streaming wrapper ──────────────────────────────────────────────────────


def _make_chunk(
    completion_id: str,
    model: str,
    *,
    content: Optional[str] = None,
    reasoning: Optional[str] = None,
    role: Optional[str] = None,
    finish_reason: Optional[FinishReason] = None,
) -> ChatCompletionChunk:
    delta_kwargs: dict[str, object] = {}
    if role is not None:
        delta_kwargs["role"] = role
    if content is not None:
        delta_kwargs["content"] = content
    if reasoning is not None:
        delta_kwargs["reasoning_content"] = reasoning
    delta = Delta(**delta_kwargs)  # type: ignore[arg-type]
    return ChatCompletionChunk(
        id=completion_id,
        model=model,
        choices=[ChunkChoice(delta=delta, finish_reason=finish_reason)],
    )


async def stream_image_generation(
    request_messages: list[Message],
    *,
    settings: Settings,
    completion_id: str,
    model_label: str,
) -> AsyncGenerator[ChatCompletionChunk, None]:
    """Stream a chat-completion response that produces a real image artifact."""
    user_message = ""
    for msg in reversed(request_messages):
        if msg.role.value != "user":
            continue
        content: MessageContent = msg.content
        if isinstance(content, str):
            user_message = content
            break
        for part in content or []:
            if hasattr(part, "text") and getattr(part, "text", None):
                user_message = part.text
                break
            if isinstance(part, dict) and part.get("type") == "text":
                user_message = part.get("text") or ""
                break
        if user_message:
            break

    image_prompt = extract_image_prompt(user_message)
    yield _make_chunk(completion_id, model_label, role="assistant")
    yield _make_chunk(
        completion_id,
        model_label,
        reasoning=f"Generating image directly via image.chutes.ai (prompt: {image_prompt!r})…\n",
    )

    api_key = (settings.chutes_api_key or "").strip()
    if not api_key:
        api_key = (settings.openai_api_key or "").strip()

    started = time.monotonic()
    try:
        image_bytes, mime_type = await generate_image(image_prompt, api_key=api_key)
    except httpx.HTTPStatusError as exc:
        body_preview = (exc.response.text or "")[:300]
        logger.warning(
            "direct_image_generation_failed status=%s body=%s",
            exc.response.status_code,
            body_preview,
        )
        yield _make_chunk(
            completion_id,
            model_label,
            content=(
                "Sorry — image generation failed "
                f"({exc.response.status_code} from image.chutes.ai). "
                "Please try again in a moment."
            ),
            finish_reason=FinishReason.STOP,
        )
        return
    except (httpx.RequestError, asyncio.TimeoutError, RuntimeError) as exc:
        logger.warning("direct_image_generation_failed error=%s", exc)
        yield _make_chunk(
            completion_id,
            model_label,
            content=(
                "Sorry — image generation isn't available right now. "
                "Please try again shortly."
            ),
            finish_reason=FinishReason.STOP,
        )
        return

    elapsed_ms = int((time.monotonic() - started) * 1000)
    # Inline data: URL keeps things self-contained — no artifact storage,
    # no proxy, no extra fetch from the browser. The chunked delta carries
    # plain markdown the existing UI already renders.
    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    safe_alt = re.sub(r"\s+", " ", (image_prompt or "Generated image")).strip()
    if not safe_alt:
        safe_alt = "Generated image"
    markdown_link = f"![{safe_alt}]({data_url})"

    yield _make_chunk(
        completion_id,
        model_label,
        reasoning=f"Image ready ({len(image_bytes)} bytes, {elapsed_ms} ms).\n",
    )
    yield _make_chunk(
        completion_id,
        model_label,
        content=f"Here is the image you asked for:\n\n{markdown_link}\n",
        finish_reason=FinishReason.STOP,
    )
