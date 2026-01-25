"""Image generation tool for the LangChain baseline."""

import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.services import get_request_auth_token

DEFAULT_IMAGE_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
DEFAULT_IMAGE_SIZE = "1024x1024"


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
        "n": 1,
        "size": DEFAULT_IMAGE_SIZE,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = _post_with_retries(
            f"{settings.chutes_api_base.rstrip('/')}/images/generations",
            headers=headers,
            payload=payload,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Image generation failed: {exc}"

    try:
        data = response.json()
    except ValueError as exc:
        return f"Image generation failed: {exc}"

    items = data.get("data") or []
    if not items:
        return "Image generation failed: empty response."

    first = items[0]
    if isinstance(first, dict):
        url = first.get("url")
        if isinstance(url, str) and url:
            return url
        b64_data = first.get("b64_json")
        if isinstance(b64_data, str) and b64_data:
            return f"data:image/png;base64,{b64_data}"

    return "Image generation failed: invalid response format."


image_generation_tool = image_generation
