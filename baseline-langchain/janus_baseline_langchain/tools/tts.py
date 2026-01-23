"""Text-to-speech tool for the LangChain baseline."""

import base64
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings


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


@tool("text_to_speech")
def text_to_speech(text: str, voice: str = "am_michael") -> str:
    """Convert text to speech audio."""
    settings = get_settings()
    if not settings.chutes_api_key:
        return "Text-to-speech unavailable: missing API key."

    payload = {"text": text, "voice": voice, "speed": 1.0}
    headers = {
        "Authorization": f"Bearer {settings.chutes_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = _post_with_retries(
            "https://chutes-kokoro.chutes.ai/speak",
            headers=headers,
            payload=payload,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Text-to-speech failed: {exc}"

    audio_data = base64.b64encode(response.content).decode("utf-8")
    return f"data:audio/wav;base64,{audio_data}"


text_to_speech_tool = text_to_speech
tts_tool = text_to_speech
