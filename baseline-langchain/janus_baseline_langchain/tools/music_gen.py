"""Music generation tool for the LangChain baseline."""

import base64
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings

DIFFRHYTHM_URL = "https://chutes-diffrhythm.chutes.ai/generate"
DEFAULT_STEPS = 32
MAX_TIMEOUT = 120.0


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


@tool("music_generation")
def music_generation(
    style_prompt: str,
    lyrics: str | None = None,
    steps: int = DEFAULT_STEPS,
) -> str:
    """Generate music using DiffRhythm."""
    settings = get_settings()
    if not settings.chutes_api_key:
        return "Music generation unavailable: missing API key."

    payload = {
        "steps": steps,
        "lyrics": lyrics,
        "style_prompt": style_prompt,
    }
    headers = {
        "Authorization": f"Bearer {settings.chutes_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = _post_with_retries(
            DIFFRHYTHM_URL,
            headers=headers,
            payload=payload,
            timeout=MAX_TIMEOUT,
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Music generation failed: {exc}"

    audio_data = base64.b64encode(response.content).decode("utf-8")
    return f"data:audio/wav;base64,{audio_data}"


music_generation_tool = music_generation
