"""Text-to-speech proxy routes."""

from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from janus_gateway.config import get_settings

router = APIRouter(prefix="/api", tags=["tts"])

TTS_ENDPOINT = "https://chutes-kokoro.chutes.ai/speak"


class TTSRequest(BaseModel):
    """Request payload for text-to-speech."""

    text: str = Field(..., min_length=1)
    voice: str = "af_sky"
    speed: float = 1.0


@router.post("/tts")
async def generate_tts(request: TTSRequest) -> Response:
    """Proxy TTS requests to Chutes Kokoro API."""

    settings = get_settings()
    api_key = settings.chutes_api_key

    if not api_key:
        raise HTTPException(status_code=503, detail="TTS service not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                TTS_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "text": request.text,
                    "voice": request.voice,
                    "speed": request.speed,
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS failed: {response.text}",
                )

            content_type = response.headers.get("content-type", "audio/wav")
            return Response(content=response.content, media_type=content_type)

        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="TTS timed out") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"TTS service error: {exc}") from exc
