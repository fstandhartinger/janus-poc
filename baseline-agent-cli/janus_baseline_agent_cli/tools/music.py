"""Music generation helper for the baseline agent CLI."""

from __future__ import annotations

import base64
import os
from typing import Optional

import httpx

DIFFRHYTHM_URL = "https://chutes-diffrhythm.chutes.ai/generate"


async def generate_music(
    style_prompt: str,
    lyrics: Optional[str] = None,
    steps: int = 32,
) -> dict:
    """Generate music using the DiffRhythm API."""
    api_key = os.environ.get("CHUTES_API_KEY")
    if not api_key:
        return {"success": False, "error": "CHUTES_API_KEY not configured"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                DIFFRHYTHM_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "steps": steps,
                    "lyrics": lyrics,
                    "style_prompt": style_prompt,
                },
            )
            response.raise_for_status()
    except Exception as exc:
        return {"success": False, "error": f"Music generation failed: {exc}"}

    audio_b64 = base64.b64encode(response.content).decode("utf-8")
    return {
        "success": True,
        "audio_url": f"data:audio/wav;base64,{audio_b64}",
        "format": "wav",
        "style": style_prompt,
        "has_vocals": lyrics is not None,
    }


MUSIC_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_music",
        "description": "Generate music or songs using AI. Can create instrumentals or full songs with vocals.",
        "parameters": {
            "type": "object",
            "properties": {
                "style_prompt": {
                    "type": "string",
                    "description": "Musical style (e.g., 'Pop ballad with piano', 'Lo-fi hip-hop beats')",
                },
                "lyrics": {
                    "type": "string",
                    "description": "LRC format lyrics with timestamps. Omit for instrumental.",
                },
                "steps": {
                    "type": "integer",
                    "default": 32,
                    "description": "Quality steps (32 default, 50+ for higher quality)",
                },
            },
            "required": ["style_prompt"],
        },
    },
}
