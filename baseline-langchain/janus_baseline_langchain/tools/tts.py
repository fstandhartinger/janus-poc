"""Text-to-speech tool for the LangChain baseline."""

import base64
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings

KOKORO_URL = "https://chutes-kokoro.chutes.ai/speak"

# Voice recommendations
VOICES = {
    # American Female
    "af_heart": "Warm, expressive (recommended)",
    "af_bella": "Clear, professional",
    "af_sarah": "Natural conversational",
    "af_nicole": "Friendly",
    "af_sky": "Light, airy",
    # American Male
    "am_fenrir": "Deep, authoritative",
    "am_michael": "Professional",
    "am_puck": "Energetic",
    # British
    "bf_emma": "British female",
    "bm_george": "British male",
    # Other languages
    "jf_alpha": "Japanese female",
    "zf_xiaoxiao": "Chinese female",
    "ef_dora": "Spanish female",
    "ff_siwis": "French female",
}


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
def text_to_speech(text: str, voice: str = "af_heart", speed: float = 1.0) -> str:
    """Convert text to natural speech using Kokoro TTS."""
    settings = get_settings()
    if not settings.chutes_api_key:
        return "Error: CHUTES_API_KEY not configured"

    speed = max(0.5, min(2.0, speed))

    payload = {"text": text, "voice": voice, "speed": speed}
    headers = {
        "Authorization": f"Bearer {settings.chutes_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = _post_with_retries(
            KOKORO_URL,
            headers=headers,
            payload=payload,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
        )
    except httpx.HTTPStatusError as exc:
        return f"Error: TTS failed - {exc.response.status_code}"
    except Exception as exc:
        return f"Error: {exc}"

    audio_data = base64.b64encode(response.content).decode("utf-8")
    return f""":::audio[type=speech,voice={voice}]\ndata:audio/wav;base64,{audio_data}\n:::"""


text_to_speech_tool = text_to_speech
tts_tool = text_to_speech
