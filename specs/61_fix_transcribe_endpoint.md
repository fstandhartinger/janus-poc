# Spec 60: Fix Transcribe Endpoint (503 Error)

## Status: COMPLETE

Note: Code improvements complete. Manual step remaining: Configure `CHUTES_API_KEY` in Render dashboard.

## Context / Why

The microphone button in the chat UI is not working. When users click the microphone button to record and transcribe audio, they receive a 503 error:

```
POST https://janus-gateway-bqou.onrender.com/api/transcribe 503 (Service Unavailable)
```

The error originates from the gateway's transcription router which returns 503 when the `CHUTES_API_KEY` environment variable is not configured:

```python
# gateway/janus_gateway/routers/transcription.py:38-39
if not api_key:
    raise HTTPException(status_code=503, detail="Transcription service not configured")
```

## Root Cause Analysis

1. **Missing Environment Variable**: The `CHUTES_API_KEY` is defined in `render.yaml` with `sync: false`, meaning it must be manually set in the Render dashboard. It appears this was never configured for the gateway service.

2. **Whisper Endpoint Verification Needed**: The current endpoint `https://chutes-whisper-large-v3.chutes.ai/transcribe` may need verification that it's still active and correctly formatted.

3. **Poor Error Feedback**: The 503 error message doesn't clearly indicate to users that voice input is temporarily unavailable.

## Goals

- Configure `CHUTES_API_KEY` on Render for the gateway service
- Verify and update the Whisper endpoint if needed
- Add better error handling and user feedback
- Add a health check for transcription service availability
- Improve logging for transcription failures

## Non-Goals

- Changing the voice recording UI
- Adding alternative transcription providers
- Local/offline transcription

## Functional Requirements

### FR-1: Configure Environment Variable on Render

**Manual Action Required**: Set `CHUTES_API_KEY` in Render dashboard:

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select `janus-gateway` service
3. Navigate to Environment → Environment Variables
4. Add/Update `CHUTES_API_KEY` with a valid Chutes API key
5. Click "Save Changes" (triggers automatic redeploy)

### FR-2: Verify Whisper Endpoint

The current endpoint needs verification. Update if the Chutes API format has changed:

```python
# gateway/janus_gateway/routers/transcription.py

# Option A: Current format (Chutes direct)
WHISPER_ENDPOINT = "https://chutes-whisper-large-v3.chutes.ai/transcribe"

# Option B: OpenAI-compatible format (if Chutes uses this)
WHISPER_ENDPOINT = "https://api.chutes.ai/v1/audio/transcriptions"

# Option C: Configurable endpoint
WHISPER_ENDPOINT = os.environ.get(
    "WHISPER_ENDPOINT",
    "https://chutes-whisper-large-v3.chutes.ai/transcribe"
)
```

### FR-3: Add Transcription Health Check

```python
# gateway/janus_gateway/routers/transcription.py

from fastapi import APIRouter, HTTPException, status
from typing import Optional
import httpx

router = APIRouter(prefix="/api", tags=["transcription"])

WHISPER_ENDPOINT = os.environ.get(
    "WHISPER_ENDPOINT",
    "https://chutes-whisper-large-v3.chutes.ai/transcribe"
)


class TranscriptionHealthResponse(BaseModel):
    """Health check response for transcription service."""
    available: bool
    endpoint: str
    api_key_configured: bool
    error: Optional[str] = None


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

    if not api_key:
        return TranscriptionHealthResponse(
            available=False,
            endpoint=WHISPER_ENDPOINT,
            api_key_configured=False,
            error="CHUTES_API_KEY not configured",
        )

    # Quick ping to verify endpoint (optional, can be slow)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Just check if endpoint responds (OPTIONS or HEAD)
            response = await client.options(WHISPER_ENDPOINT)
            # Any response (even 405) means endpoint is reachable
            reachable = response.status_code < 500
    except Exception as e:
        return TranscriptionHealthResponse(
            available=False,
            endpoint=WHISPER_ENDPOINT,
            api_key_configured=True,
            error=f"Endpoint unreachable: {str(e)}",
        )

    return TranscriptionHealthResponse(
        available=reachable,
        endpoint=WHISPER_ENDPOINT,
        api_key_configured=True,
    )
```

### FR-4: Improved Error Handling

```python
# gateway/janus_gateway/routers/transcription.py

import logging
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)


class TranscriptionError(BaseModel):
    """Detailed transcription error response."""
    error: str
    code: str
    recoverable: bool
    suggestion: Optional[str] = None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest) -> TranscriptionResponse:
    """Proxy transcription requests to Chutes Whisper API."""

    settings = get_settings()
    api_key = settings.chutes_api_key

    if not api_key:
        logger.error("Transcription failed: CHUTES_API_KEY not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Voice transcription is temporarily unavailable",
                "code": "TRANSCRIPTION_NOT_CONFIGURED",
                "recoverable": False,
                "suggestion": "Please type your message instead",
            },
        )

    # Validate audio data
    if not request.audio_b64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "No audio data provided",
                "code": "MISSING_AUDIO",
                "recoverable": True,
                "suggestion": "Please record audio before submitting",
            },
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logger.info(f"Sending transcription request to {WHISPER_ENDPOINT}")

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

            logger.info(f"Transcription response: {response.status_code}")

            if response.status_code == 401:
                logger.error("Transcription failed: Invalid API key")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "Voice transcription authentication failed",
                        "code": "INVALID_API_KEY",
                        "recoverable": False,
                        "suggestion": "Please type your message instead",
                    },
                )

            if response.status_code == 429:
                logger.warning("Transcription rate limited")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Too many transcription requests",
                        "code": "RATE_LIMITED",
                        "recoverable": True,
                        "suggestion": "Please wait a moment and try again",
                    },
                )

            if response.status_code != 200:
                logger.error(f"Transcription failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "error": f"Transcription failed: {response.text}",
                        "code": "UPSTREAM_ERROR",
                        "recoverable": True,
                        "suggestion": "Please try again",
                    },
                )

            result = response.json()
            text = result.get("text", result.get("transcription", ""))

            if not text:
                logger.warning("Transcription returned empty text")

            logger.info(f"Transcription successful: {len(text)} characters")

            return TranscriptionResponse(
                text=text,
                language=result.get("language"),
                duration=result.get("duration"),
            )

        except httpx.TimeoutException as exc:
            logger.error(f"Transcription timed out: {exc}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error": "Transcription timed out",
                    "code": "TIMEOUT",
                    "recoverable": True,
                    "suggestion": "Please try a shorter recording",
                },
            ) from exc

        except httpx.RequestError as exc:
            logger.error(f"Transcription request error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Could not reach transcription service",
                    "code": "SERVICE_UNREACHABLE",
                    "recoverable": True,
                    "suggestion": "Please try again in a moment",
                },
            ) from exc
```

### FR-5: UI Error Handling Improvements

```typescript
// ui/src/lib/transcription.ts

export interface TranscriptionError {
  error: string;
  code: string;
  recoverable: boolean;
  suggestion?: string;
}

export async function transcribeViaGateway(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  const base64 = await blobToBase64(audioBlob);

  const response = await fetch(`${GATEWAY_URL}/api/transcribe`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      language: options.language ?? null,
      audio_b64: base64,
    }),
  });

  if (!response.ok) {
    let errorData: TranscriptionError;

    try {
      const data = await response.json();
      errorData = data.detail || data;
    } catch {
      errorData = {
        error: 'Transcription failed',
        code: 'UNKNOWN',
        recoverable: true,
        suggestion: 'Please try again',
      };
    }

    throw new TranscriptionFailedError(
      errorData.error,
      errorData.code,
      errorData.recoverable,
      errorData.suggestion
    );
  }

  return response.json();
}

export class TranscriptionFailedError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly recoverable: boolean,
    public readonly suggestion?: string
  ) {
    super(message);
    this.name = 'TranscriptionFailedError';
  }
}
```

### FR-6: Voice Input Button Error Display

```tsx
// ui/src/components/VoiceInputButton.tsx

import { TranscriptionFailedError } from '@/lib/transcription';

// In the component's error handling:
const handleTranscriptionError = (error: unknown) => {
  if (error instanceof TranscriptionFailedError) {
    setError(error.suggestion || error.message);

    if (!error.recoverable) {
      // Show persistent warning that voice input is unavailable
      setVoiceInputDisabled(true);
    }
  } else {
    setError('Voice input failed. Please type your message.');
  }
};

// In the JSX, show helpful error message:
{error && (
  <div className="text-sm text-red-400 mt-2">
    {error}
  </div>
)}

{voiceInputDisabled && (
  <div className="text-xs text-yellow-400 mt-1">
    Voice input is temporarily unavailable
  </div>
)}
```

### FR-7: Add Startup Health Check

```python
# gateway/janus_gateway/main.py

import logging
from janus_gateway.config import get_settings

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_health_checks():
    """Run health checks on startup and log warnings for missing configs."""
    settings = get_settings()

    # Check transcription service
    if not settings.chutes_api_key:
        logger.warning(
            "CHUTES_API_KEY not configured - transcription endpoint will return 503. "
            "Set CHUTES_API_KEY environment variable to enable voice transcription."
        )
    else:
        logger.info("Transcription service configured")

    # Check other services...
```

## Deployment Steps

### Step 1: Set Environment Variable (Immediate Fix)

1. Log into [Render Dashboard](https://dashboard.render.com)
2. Go to `janus-gateway` service
3. Click "Environment" in the left sidebar
4. Find or add `CHUTES_API_KEY`
5. Set value to a valid Chutes API key
6. Click "Save Changes"
7. Wait for automatic redeploy (~2-3 minutes)

### Step 2: Verify Fix

```bash
# Test transcription health endpoint
curl https://janus-gateway-bqou.onrender.com/api/transcribe/health

# Expected response when configured:
# {"available": true, "endpoint": "...", "api_key_configured": true}

# Test transcription with sample audio
curl -X POST https://janus-gateway-bqou.onrender.com/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{"audio_b64": "...", "language": "en"}'
```

### Step 3: Deploy Code Changes

After implementing the improved error handling:

```bash
cd gateway
pytest tests/test_transcription.py
git add -A && git commit -m "Improve transcription error handling"
git push
```

## Environment Variables

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `CHUTES_API_KEY` | janus-gateway | Yes | Chutes API key for Whisper |
| `WHISPER_ENDPOINT` | janus-gateway | No | Override default Whisper URL |

## Acceptance Criteria

- [ ] `CHUTES_API_KEY` configured on Render
- [ ] `/api/transcribe/health` endpoint returns `available: true`
- [ ] Microphone button in UI works for recording
- [ ] Audio successfully transcribed to text
- [ ] Transcribed text appears in input field
- [ ] Clear error messages shown when service unavailable
- [ ] Startup logs show transcription service status
- [ ] Tests pass

## Files to Modify

```
gateway/
├── janus_gateway/
│   ├── main.py                    # Add startup health check
│   └── routers/
│       └── transcription.py       # Improve error handling, add health endpoint
└── tests/
    └── test_transcription.py      # Add health check tests

ui/
├── src/
│   ├── lib/
│   │   └── transcription.ts       # Add error types
│   └── components/
│       └── VoiceInputButton.tsx   # Better error display
```

## Rollback Plan

If issues persist after configuration:

1. Check Render logs for specific error messages
2. Verify Whisper endpoint is accessible: `curl -I https://chutes-whisper-large-v3.chutes.ai`
3. Test with direct API call to isolate gateway vs upstream issues
4. If Chutes endpoint changed, update `WHISPER_ENDPOINT` environment variable

## Related Specs

- `specs/39_speech_to_text_voice_input.md` - Original voice input implementation
- `specs/47_text_to_speech_response_playback.md` - TTS (reverse direction)

## References

- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Chutes AI Documentation](https://chutes.ai/docs)
