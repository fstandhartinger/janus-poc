"""Image generation tool for the LangChain baseline."""

import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.services import add_artifact, get_artifact_manager, get_request_auth_token

IMAGE_API_URL = "https://image.chutes.ai/generate"
DEFAULT_IMAGE_MODEL = "qwen-image"
DEFAULT_IMAGE_WIDTH = 1024
DEFAULT_IMAGE_HEIGHT = 1024
DEFAULT_IMAGE_STEPS = 30


def _post_with_retries(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    max_retries: int,
) -> httpx.Response:
    last_exc: Exception | None = None
    attempts = max(1, max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(0.5 * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("Request failed")


@tool("image_generation")
def image_generation(prompt: str) -> str:
    """Generate an image from a text description."""
    settings = get_settings()
    token = get_request_auth_token() or settings.chutes_api_key
    if not token:
        return "Image generation unavailable: missing API key."

    payload = {
        "model": DEFAULT_IMAGE_MODEL,
        "prompt": prompt,
        "width": DEFAULT_IMAGE_WIDTH,
        "height": DEFAULT_IMAGE_HEIGHT,
        "num_inference_steps": DEFAULT_IMAGE_STEPS,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = _post_with_retries(
            IMAGE_API_URL,
            headers=headers,
            payload=payload,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Image generation failed: {exc}"

    if not response.content:
        return "Image generation failed: empty response."

    content_type = response.headers.get("content-type", "image/png")
    ext = ".jpg" if "jpeg" in content_type else ".png"
    manager = get_artifact_manager()
    artifact = manager.create_artifact(
        f"generated-image{ext}",
        response.content,
        content_type,
    )
    add_artifact(artifact)
    return f"Image generated: {artifact.url}"


image_generation_tool = image_generation
