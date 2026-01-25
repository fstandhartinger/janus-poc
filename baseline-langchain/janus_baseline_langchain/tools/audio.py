"""Audio generation tool for the LangChain baseline."""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.services import add_artifact, get_artifact_manager, get_request_auth_token

KOKORO_URL = "https://chutes-kokoro.chutes.ai/speak"
DIFFRHYTHM_URL = "https://chutes-diffrhythm.chutes.ai/generate"
DEFAULT_AUDIO_MIME = "audio/wav"
DEFAULT_STEPS = 32
MUSIC_TIMEOUT = 120.0


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


@tool("audio_generation")
def audio_generation(prompt: str, type: str = "music") -> str:  # noqa: A002
    """Generate audio or music from a text prompt using Chutes."""
    settings = get_settings()
    token = get_request_auth_token() or settings.chutes_api_key
    if not token:
        return "Audio generation unavailable: missing API key."

    manager = get_artifact_manager()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if type.lower() in {"speech", "tts", "voice"}:
        payload = {"text": prompt, "voice": "af_heart", "speed": 1.0}
        try:
            response = _post_with_retries(
                KOKORO_URL,
                headers=headers,
                payload=payload,
                timeout=settings.request_timeout,
                max_retries=settings.max_retries,
            )
        except Exception as exc:
            return f"Audio generation failed: {exc}"
        audio_bytes = response.content
        artifact = manager.create_artifact("speech.wav", audio_bytes, DEFAULT_AUDIO_MIME)
        add_artifact(artifact)
        audio_data = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/wav;base64,{audio_data}"

    payload = {"steps": DEFAULT_STEPS, "lyrics": None, "style_prompt": prompt}
    try:
        response = _post_with_retries(
            DIFFRHYTHM_URL,
            headers=headers,
            payload=payload,
            timeout=max(settings.request_timeout, MUSIC_TIMEOUT),
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Audio generation failed: {exc}"

    audio_bytes = response.content
    artifact = manager.create_artifact("music.wav", audio_bytes, DEFAULT_AUDIO_MIME)
    add_artifact(artifact)
    audio_data = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:audio/wav;base64,{audio_data}"


audio_generation_tool = audio_generation
