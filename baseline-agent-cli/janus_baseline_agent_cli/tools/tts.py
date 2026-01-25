"""Text-to-speech helper for the baseline agent CLI."""

from __future__ import annotations

import base64
import os

import httpx

KOKORO_URL = "https://chutes-kokoro.chutes.ai/speak"


async def generate_speech(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0,
) -> dict:
    """Generate speech using the Kokoro TTS API."""
    api_key = os.environ.get("CHUTES_API_KEY")
    if not api_key:
        return {"success": False, "error": "CHUTES_API_KEY not configured"}

    speed = max(0.5, min(2.0, speed))

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                KOKORO_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "voice": voice,
                    "speed": speed,
                },
            )
            response.raise_for_status()
    except Exception as exc:
        return {"success": False, "error": f"TTS generation failed: {exc}"}

    audio_b64 = base64.b64encode(response.content).decode("utf-8")
    return {
        "success": True,
        "audio_url": f"data:audio/wav;base64,{audio_b64}",
        "format": "wav",
        "voice": voice,
        "text_length": len(text),
    }


TTS_TOOL = {
    "type": "function",
    "function": {
        "name": "text_to_speech",
        "description": "Convert text to natural speech. Supports 54+ voices in 8 languages.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech",
                },
                "voice": {
                    "type": "string",
                    "default": "af_heart",
                    "description": "Voice ID (e.g., af_heart, am_michael, bf_emma)",
                },
                "speed": {
                    "type": "number",
                    "default": 1.0,
                    "description": "Speech speed (0.5 to 2.0)",
                },
            },
            "required": ["text"],
        },
    },
}
