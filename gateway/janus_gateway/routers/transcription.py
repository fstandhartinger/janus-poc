"""Transcription proxy routes."""

from typing import Any, Optional

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from janus_gateway.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["transcription"])


class TranscriptionRequest(BaseModel):
    """Request payload for transcription."""

    audio_b64: str
    language: Optional[str] = None


class TranscriptionResponse(BaseModel):
    """Response payload for transcription."""

    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


class TranscriptionHealthResponse(BaseModel):
    """Health check response for transcription service."""

    available: bool
    endpoint: str
    api_key_configured: bool
    error: Optional[str] = None


class TranscriptionErrorDetail(BaseModel):
    """Detailed transcription error response."""

    error: str
    code: str
    recoverable: bool
    suggestion: Optional[str] = None


def create_error_response(
    error: str,
    code: str,
    recoverable: bool,
    suggestion: Optional[str] = None,
) -> dict[str, Any]:
    """Create a structured error response."""
    return {
        "error": error,
        "code": code,
        "recoverable": recoverable,
        "suggestion": suggestion,
    }


@router.get("/transcribe/health", response_model=TranscriptionHealthResponse)
async def transcription_health() -> TranscriptionHealthResponse:
    """
    Check if transcription service is available.

    Returns status of:
    - API key configuration
    - Whisper endpoint reachability
    """
    settings = get_settings()
    api_key = settings.chutes_api_key
    whisper_endpoint = settings.whisper_endpoint

    if not api_key:
        return TranscriptionHealthResponse(
            available=False,
            endpoint=whisper_endpoint,
            api_key_configured=False,
            error="CHUTES_API_KEY not configured",
        )

    # Quick ping to verify endpoint (optional, can be slow)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Just check if endpoint responds (OPTIONS or HEAD)
            response = await client.options(whisper_endpoint)
            # Any response (even 405) means endpoint is reachable
            reachable = response.status_code < 500
    except Exception as e:
        logger.warning("transcription_endpoint_unreachable", error=str(e))
        return TranscriptionHealthResponse(
            available=False,
            endpoint=whisper_endpoint,
            api_key_configured=True,
            error=f"Endpoint unreachable: {str(e)}",
        )

    return TranscriptionHealthResponse(
        available=reachable,
        endpoint=whisper_endpoint,
        api_key_configured=True,
    )


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest) -> TranscriptionResponse:
    """Proxy transcription requests to Chutes Whisper API."""

    settings = get_settings()
    api_key = settings.chutes_api_key
    whisper_endpoint = settings.whisper_endpoint

    if not api_key:
        logger.error("transcription_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                error="Voice transcription is temporarily unavailable",
                code="TRANSCRIPTION_NOT_CONFIGURED",
                recoverable=False,
                suggestion="Please type your message instead",
            ),
        )

    # Validate audio data
    if not request.audio_b64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                error="No audio data provided",
                code="MISSING_AUDIO",
                recoverable=True,
                suggestion="Please record audio before submitting",
            ),
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logger.info("transcription_request_sent", endpoint=whisper_endpoint)

            response = await client.post(
                whisper_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "language": request.language,
                    "audio_b64": request.audio_b64,
                },
            )

            logger.info("transcription_response", status_code=response.status_code)

            if response.status_code == 401:
                logger.error("transcription_invalid_api_key")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=create_error_response(
                        error="Voice transcription authentication failed",
                        code="INVALID_API_KEY",
                        recoverable=False,
                        suggestion="Please type your message instead",
                    ),
                )

            if response.status_code == 429:
                logger.warning("transcription_rate_limited")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=create_error_response(
                        error="Too many transcription requests",
                        code="RATE_LIMITED",
                        recoverable=True,
                        suggestion="Please wait a moment and try again",
                    ),
                )

            if response.status_code != 200:
                logger.error(
                    "transcription_failed",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=create_error_response(
                        error=f"Transcription failed: {response.text}",
                        code="UPSTREAM_ERROR",
                        recoverable=True,
                        suggestion="Please try again",
                    ),
                )

            result = response.json()
            text = result.get("text", result.get("transcription", ""))

            if not text:
                logger.warning("transcription_empty_text")

            logger.info("transcription_successful", char_count=len(text))

            return TranscriptionResponse(
                text=text,
                language=result.get("language"),
                duration=result.get("duration"),
            )

        except httpx.TimeoutException as exc:
            logger.error("transcription_timeout", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=create_error_response(
                    error="Transcription timed out",
                    code="TIMEOUT",
                    recoverable=True,
                    suggestion="Please try a shorter recording",
                ),
            ) from exc

        except httpx.RequestError as exc:
            logger.error("transcription_request_error", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=create_error_response(
                    error="Could not reach transcription service",
                    code="SERVICE_UNREACHABLE",
                    recoverable=True,
                    suggestion="Please try again in a moment",
                ),
            ) from exc
