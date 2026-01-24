"""Transcription proxy routes."""

from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from janus_gateway.config import get_settings

router = APIRouter(prefix="/api", tags=["transcription"])

WHISPER_ENDPOINT = "https://chutes-whisper-large-v3.chutes.ai/transcribe"


class TranscriptionRequest(BaseModel):
    """Request payload for transcription."""

    audio_b64: str
    language: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response payload for transcription."""

    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest) -> TranscriptionResponse:
    """Proxy transcription requests to Chutes Whisper API."""

    settings = get_settings()
    api_key = settings.chutes_api_key

    if not api_key:
        raise HTTPException(status_code=503, detail="Transcription service not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                WHISPER_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "language": request.language,
                    "audio_b64": request.audio_b64,
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Transcription failed: {response.text}",
                )

            result = response.json()
            return TranscriptionResponse(
                text=result.get("text", result.get("transcription", "")),
                language=result.get("language"),
                duration=result.get("duration"),
            )

        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Transcription timed out") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Transcription service error: {exc}") from exc
