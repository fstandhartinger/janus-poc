# Spec 83: Fix Transcription API

**Status:** COMPLETE
**Priority:** High
**Complexity:** Medium
**Prerequisites:** None

---

## Overview

Fix the microphone transcription feature in the chat UI. Currently getting 400 Bad Request errors when trying to transcribe audio.

---

## Problem

**Error:**
```
POST https://janus-gateway-bqou.onrender.com/api/transcribe 400 (Bad Request)

{
  "detail": "Transcription failed: {\"detail\":\"Invalid request: Invalid request: {\\\"detail\\\":\\\"Invalid input parameters\\\"}\"}"
}
```

The error is nested, indicating the gateway is forwarding an error from the upstream transcription service, which itself is returning an error about invalid input parameters.

---

## Investigation Required

### IR-1: Check Gateway Transcribe Endpoint

Locate and review the gateway's `/api/transcribe` endpoint:
- What format does it expect?
- How does it forward to the upstream service?
- What validation is performed?

### IR-2: Check UI Request Format

Review how the UI sends audio data:
- Is it sending as FormData with file?
- Is it sending as base64 in JSON?
- What content-type header is being used?
- What audio format (wav, webm, mp3)?

### IR-3: Check Upstream Transcription Service

Identify which service handles transcription:
- Is it Chutes API?
- Is it a custom service?
- What format does it expect?

---

## Potential Causes

### PC-1: Content-Type Mismatch
The UI might be sending the wrong content type. Whisper-compatible APIs typically expect:
- `multipart/form-data` with `file` field
- Audio file in supported format (wav, mp3, webm, etc.)

### PC-2: Audio Format Issue
The browser's MediaRecorder might be producing:
- webm/opus (common in Chrome)
- audio/mp4 (Safari)
- audio/ogg (Firefox)

Some transcription services only accept specific formats.

### PC-3: Missing Required Fields
The Whisper API requires:
- `file` - the audio file
- `model` - e.g., "whisper-1"

### PC-4: Base64 vs File Upload
The UI might be sending base64 encoded audio when the API expects a file upload, or vice versa.

### PC-5: Null Language Field
Sending `"language": null` can cause the upstream service to reject the request as invalid input parameters. Omit the field when it is not set.

---

## Functional Requirements

### FR-1: Fix Gateway Transcribe Endpoint

Ensure proper request forwarding:

```python
# gateway/janus_gateway/routers/transcribe.py

@router.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default="whisper-1"),
    language: str | None = Form(default=None),
):
    """Transcribe audio file using Chutes Whisper API."""
    try:
        # Read file content
        content = await file.read()

        # Forward to Chutes API
        async with httpx.AsyncClient() as client:
            files = {
                "file": (file.filename or "audio.webm", content, file.content_type),
            }
            data = {"model": model}
            if language:
                data["language"] = language

            response = await client.post(
                f"{settings.chutes_api_base}/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.chutes_api_key}"},
                files=files,
                data=data,
                timeout=60.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Transcription failed: {response.text}",
                )

            return response.json()

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Transcription service error: {str(e)}")
```

### FR-2: Fix UI Audio Recording & Upload

Ensure proper audio format and upload:

```typescript
// lib/audio-recorder.ts

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];

  async start(): Promise<void> {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Prefer webm/opus, fallback to other formats
    const mimeType = this.getSupportedMimeType();

    this.mediaRecorder = new MediaRecorder(stream, { mimeType });
    this.chunks = [];

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        this.chunks.push(e.data);
      }
    };

    this.mediaRecorder.start();
  }

  stop(): Promise<Blob> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(new Blob());
        return;
      }

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: this.mediaRecorder?.mimeType });
        this.cleanup();
        resolve(blob);
      };

      this.mediaRecorder.stop();
    });
  }

  private getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/wav',
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return 'audio/webm';  // Default fallback
  }

  private cleanup(): void {
    if (this.mediaRecorder?.stream) {
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    this.mediaRecorder = null;
    this.chunks = [];
  }
}
```

### FR-3: Fix Transcription API Call

```typescript
// lib/api.ts

export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData();

  // Determine file extension from mime type
  const mimeType = audioBlob.type;
  const extension = mimeType.includes('webm') ? 'webm'
    : mimeType.includes('mp4') ? 'm4a'
    : mimeType.includes('ogg') ? 'ogg'
    : mimeType.includes('wav') ? 'wav'
    : 'webm';

  formData.append('file', audioBlob, `recording.${extension}`);
  formData.append('model', 'whisper-1');

  const response = await fetch('/api/transcribe', {
    method: 'POST',
    body: formData,
    // Don't set Content-Type header - browser will set it with boundary
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Transcription failed');
  }

  const result = await response.json();
  return result.text;
}
```

### FR-4: Add Error Handling in UI

```typescript
// components/ChatInput.tsx (or wherever recording is handled)

const handleTranscribe = async (audioBlob: Blob) => {
  try {
    setTranscribing(true);
    const text = await transcribeAudio(audioBlob);
    if (text) {
      setInputValue(prev => prev + (prev ? ' ' : '') + text);
    }
  } catch (error) {
    console.error('Transcription error:', error);
    toast.error('Failed to transcribe audio. Please try again.');
  } finally {
    setTranscribing(false);
  }
};
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `gateway/janus_gateway/routers/transcribe.py` | Fix request forwarding |
| `ui/src/lib/api.ts` | Fix transcribeAudio function |
| `ui/src/lib/audio-recorder.ts` | Ensure proper audio format |
| `ui/src/components/ChatInput.tsx` | Better error handling |

---

## Testing Checklist

- [ ] Click microphone button starts recording
- [ ] Recording indicator shows while recording
- [ ] Stop recording sends audio to transcribe endpoint
- [ ] Gateway properly forwards to Chutes API
- [ ] Successful transcription returns text
- [ ] Text is inserted into input field
- [ ] Error displays user-friendly message
- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari (if possible)

---

## Debugging Steps

1. **Check network request in browser DevTools:**
   - Is it sending `multipart/form-data`?
   - Is the `file` field present?
   - What's the file mime type?

2. **Check gateway logs:**
   - Is the request received correctly?
   - What's being sent to upstream?
   - What error comes back?

3. **Test Chutes API directly:**
   ```bash
   curl -X POST https://api.chutes.ai/v1/audio/transcriptions \
     -H "Authorization: Bearer $CHUTES_API_KEY" \
     -F "file=@test.webm" \
     -F "model=whisper-1"
   ```

---

## Notes

- The nested error suggests multiple layers of error handling
- Audio format compatibility is often the issue
- Browser MediaRecorder produces different formats per browser
- Consider adding audio format conversion on gateway if needed
- The current Chutes whisper endpoint accepts JSON base64 payloads; do not include a null language field
- The Chutes whisper endpoint may return a list of segment objects; assemble text when needed

NR_OF_TRIES: 1
