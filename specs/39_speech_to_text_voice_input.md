# Spec 39: Speech-to-Text Voice Input

## Status: COMPLETE

## Context / Why

The chat UI has a microphone button in the input area, but it currently does nothing. Voice input is a critical accessibility feature and convenience for users who prefer speaking over typing.

Chutes provides a Whisper Large V3 endpoint for speech-to-text transcription that we can leverage:

```bash
# Chutes Whisper API
POST https://chutes-whisper-large-v3.chutes.ai/transcribe
Content-Type: application/json
Authorization: Bearer $CHUTES_API_TOKEN

{
  "language": null,  # Optional: auto-detect or specify "en", "de", etc.
  "audio_b64": "base64_encoded_audio_data"
}
```

## Goals

- Implement functional voice recording in chat UI
- Transcribe speech using Chutes Whisper API
- Support multiple audio formats
- Provide visual feedback during recording
- Handle errors gracefully
- Support continuous/push-to-talk modes

## Non-Goals

- Real-time streaming transcription
- Speaker diarization
- Voice commands/shortcuts
- Text-to-speech (separate feature)
- Offline transcription

## Functional Requirements

### FR-1: Audio Recording Hook

```typescript
// ui/src/hooks/useAudioRecorder.ts

import { useState, useRef, useCallback } from 'react';

interface AudioRecorderState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioBlob: Blob | null;
  audioUrl: string | null;
  error: string | null;
}

interface UseAudioRecorderOptions {
  maxDuration?: number; // Max recording duration in seconds (default 120)
  sampleRate?: number;  // Audio sample rate (default 16000 for Whisper)
}

export function useAudioRecorder(options: UseAudioRecorderOptions = {}) {
  const { maxDuration = 120, sampleRate = 16000 } = options;

  const [state, setState] = useState<AudioRecorderState>({
    isRecording: false,
    isPaused: false,
    duration: 0,
    audioBlob: null,
    audioUrl: null,
    error: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      chunksRef.current = [];

      // Prefer webm/opus for good quality and small size
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);

        setState((prev) => ({
          ...prev,
          isRecording: false,
          audioBlob,
          audioUrl,
        }));

        // Stop all tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = (event) => {
        setState((prev) => ({
          ...prev,
          isRecording: false,
          error: 'Recording failed',
        }));
      };

      // Start recording
      mediaRecorder.start(1000); // Collect data every second

      // Start duration timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const duration = Math.floor((Date.now() - startTime) / 1000);
        setState((prev) => ({ ...prev, duration }));

        // Auto-stop at max duration
        if (duration >= maxDuration) {
          stopRecording();
        }
      }, 100);

      setState({
        isRecording: true,
        isPaused: false,
        duration: 0,
        audioBlob: null,
        audioUrl: null,
        error: null,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Failed to access microphone';

      setState((prev) => ({
        ...prev,
        error: message.includes('Permission')
          ? 'Microphone permission denied'
          : message,
      }));
    }
  }, [maxDuration, sampleRate]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const cancelRecording = useCallback(() => {
    stopRecording();
    chunksRef.current = [];
    setState({
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioBlob: null,
      audioUrl: null,
      error: null,
    });
  }, [stopRecording]);

  const reset = useCallback(() => {
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl);
    }
    setState({
      isRecording: false,
      isPaused: false,
      duration: 0,
      audioBlob: null,
      audioUrl: null,
      error: null,
    });
  }, [state.audioUrl]);

  return {
    ...state,
    startRecording,
    stopRecording,
    cancelRecording,
    reset,
  };
}
```

### FR-2: Transcription Service

```typescript
// ui/src/lib/transcription.ts

const WHISPER_ENDPOINT = 'https://chutes-whisper-large-v3.chutes.ai/transcribe';

interface TranscriptionOptions {
  language?: string | null; // ISO 639-1 code or null for auto-detect
}

interface TranscriptionResult {
  text: string;
  language?: string;
  duration?: number;
}

export async function transcribeAudio(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  // Convert blob to base64
  const base64 = await blobToBase64(audioBlob);

  // Get API key from environment or config
  const apiKey = process.env.NEXT_PUBLIC_CHUTES_API_KEY;
  if (!apiKey) {
    throw new Error('Chutes API key not configured');
  }

  const response = await fetch(WHISPER_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      language: options.language ?? null,
      audio_b64: base64,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Transcription failed: ${error}`);
  }

  const result = await response.json();

  return {
    text: result.text || result.transcription || '',
    language: result.language,
    duration: result.duration,
  };
}

async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      // Remove data URL prefix (e.g., "data:audio/webm;base64,")
      const base64Data = base64.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Alternative: Use gateway proxy for API key security
export async function transcribeViaGateway(
  audioBlob: Blob,
  options: TranscriptionOptions = {}
): Promise<TranscriptionResult> {
  const base64 = await blobToBase64(audioBlob);

  const response = await fetch('/api/transcribe', {
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
    throw new Error('Transcription failed');
  }

  return response.json();
}
```

### FR-3: Voice Input Button Component

```tsx
// ui/src/components/VoiceInputButton.tsx

import { useState, useCallback } from 'react';
import { Mic, MicOff, Loader2, Square } from 'lucide-react';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { transcribeViaGateway } from '@/lib/transcription';
import { cn } from '@/lib/utils';

interface VoiceInputButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export function VoiceInputButton({
  onTranscription,
  disabled,
  className,
}: VoiceInputButtonProps) {
  const [isTranscribing, setIsTranscribing] = useState(false);

  const {
    isRecording,
    duration,
    audioBlob,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
    reset,
  } = useAudioRecorder({ maxDuration: 120 });

  const handleClick = useCallback(async () => {
    if (isRecording) {
      // Stop and transcribe
      stopRecording();
    } else if (audioBlob) {
      // Transcribe existing recording
      setIsTranscribing(true);
      try {
        const result = await transcribeViaGateway(audioBlob);
        if (result.text.trim()) {
          onTranscription(result.text.trim());
        }
      } catch (err) {
        console.error('Transcription error:', err);
      } finally {
        setIsTranscribing(false);
        reset();
      }
    } else {
      // Start recording
      startRecording();
    }
  }, [isRecording, audioBlob, startRecording, stopRecording, onTranscription, reset]);

  // Auto-transcribe when recording stops
  const handleRecordingComplete = useCallback(async () => {
    if (audioBlob && !isRecording) {
      setIsTranscribing(true);
      try {
        const result = await transcribeViaGateway(audioBlob);
        if (result.text.trim()) {
          onTranscription(result.text.trim());
        }
      } catch (err) {
        console.error('Transcription error:', err);
      } finally {
        setIsTranscribing(false);
        reset();
      }
    }
  }, [audioBlob, isRecording, onTranscription, reset]);

  // Effect to auto-transcribe
  useEffect(() => {
    if (audioBlob && !isRecording && !isTranscribing) {
      handleRecordingComplete();
    }
  }, [audioBlob, isRecording, isTranscribing, handleRecordingComplete]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isTranscribing}
        className={cn(
          'w-9 h-9 rounded-full border flex items-center justify-center transition-all',
          isRecording
            ? 'bg-red-500/20 border-red-500 text-red-500 animate-pulse'
            : 'border-ink-700 text-ink-400 hover:text-ink-200 hover:border-ink-500',
          (disabled || isTranscribing) && 'opacity-50 cursor-not-allowed',
          className
        )}
        aria-label={
          isRecording
            ? 'Stop recording'
            : isTranscribing
            ? 'Transcribing...'
            : 'Start voice input'
        }
      >
        {isTranscribing ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isRecording ? (
          <Square className="w-4 h-4 fill-current" />
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </button>

      {/* Recording duration indicator */}
      {isRecording && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-red-500/20 text-red-400 text-xs font-mono whitespace-nowrap">
          {formatDuration(duration)}
        </div>
      )}

      {/* Error tooltip */}
      {error && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-2 py-1 rounded bg-red-500/90 text-white text-xs whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}
```

### FR-4: Gateway Transcription Proxy

```python
# gateway/janus_gateway/routers/transcription.py

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from janus_gateway.config import get_settings

router = APIRouter(prefix="/api", tags=["transcription"])

WHISPER_ENDPOINT = "https://chutes-whisper-large-v3.chutes.ai/transcribe"


class TranscriptionRequest(BaseModel):
    audio_b64: str
    language: Optional[str] = None


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscriptionRequest):
    """
    Proxy transcription requests to Chutes Whisper API.

    This keeps the API key server-side and adds rate limiting.
    """
    settings = get_settings()
    api_key = settings.chutes_api_key

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Transcription service not configured"
        )

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
                    detail=f"Transcription failed: {response.text}"
                )

            result = response.json()
            return TranscriptionResponse(
                text=result.get("text", result.get("transcription", "")),
                language=result.get("language"),
                duration=result.get("duration"),
            )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Transcription timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Transcription service error: {str(e)}"
            )
```

### FR-5: Update ChatInput Component

```tsx
// ui/src/components/ChatInput.tsx - Updated

import { VoiceInputButton } from './VoiceInputButton';

export function ChatInput({
  onSend,
  disabled,
  // ... other props
}: ChatInputProps) {
  const [input, setInput] = useState('');
  // ... existing state

  const handleTranscription = useCallback((text: string) => {
    // Append transcribed text to existing input
    setInput((prev) => {
      const separator = prev.trim() ? ' ' : '';
      return prev + separator + text;
    });

    // Focus the textarea
    textareaRef.current?.focus();
  }, []);

  return (
    <form onSubmit={handleSubmit} className="...">
      {/* File attachment button */}
      <button type="button" onClick={() => fileInputRef.current?.click()}>
        {/* ... */}
      </button>

      {/* Hidden file input */}
      <input ref={fileInputRef} type="file" className="hidden" />

      {/* Text input */}
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask anything..."
        disabled={disabled}
        // ...
      />

      {/* Voice input button - NOW FUNCTIONAL */}
      <VoiceInputButton
        onTranscription={handleTranscription}
        disabled={disabled}
      />

      {/* Send button */}
      <button type="submit" disabled={disabled || (!input.trim() && images.length === 0)}>
        {/* ... */}
      </button>
    </form>
  );
}
```

### FR-6: Recording Permission Dialog

```tsx
// ui/src/components/MicrophonePermissionDialog.tsx

import { useState, useEffect } from 'react';
import { Mic, AlertCircle } from 'lucide-react';

export function useMicrophonePermission() {
  const [permission, setPermission] = useState<PermissionState | 'unknown'>('unknown');

  useEffect(() => {
    // Check current permission state
    navigator.permissions
      ?.query({ name: 'microphone' as PermissionName })
      .then((result) => {
        setPermission(result.state);
        result.onchange = () => setPermission(result.state);
      })
      .catch(() => setPermission('unknown'));
  }, []);

  const requestPermission = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setPermission('granted');
      return true;
    } catch {
      setPermission('denied');
      return false;
    }
  };

  return { permission, requestPermission };
}

export function MicrophonePermissionBanner() {
  const { permission, requestPermission } = useMicrophonePermission();
  const [dismissed, setDismissed] = useState(false);

  if (permission === 'granted' || dismissed) return null;

  return (
    <div className="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
      <AlertCircle className="h-5 w-5 text-amber-500 shrink-0" />
      <p className="text-ink-300">
        {permission === 'denied'
          ? 'Microphone access was denied. Enable it in your browser settings to use voice input.'
          : 'Enable microphone access for voice input.'}
      </p>
      {permission !== 'denied' && (
        <button
          onClick={requestPermission}
          className="ml-auto shrink-0 rounded bg-amber-500/20 px-3 py-1 text-amber-400 hover:bg-amber-500/30"
        >
          Enable
        </button>
      )}
      <button
        onClick={() => setDismissed(true)}
        className="text-ink-500 hover:text-ink-300"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
```

### FR-7: Audio Waveform Visualization (Optional Enhancement)

```tsx
// ui/src/components/AudioWaveform.tsx

import { useRef, useEffect } from 'react';

interface AudioWaveformProps {
  stream: MediaStream | null;
  isActive: boolean;
}

export function AudioWaveform({ stream, isActive }: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyzerRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    if (!stream || !isActive || !canvasRef.current) return;

    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);

    analyser.fftSize = 256;
    source.connect(analyser);
    analyzerRef.current = analyser;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d')!;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;

        // Use moss green gradient
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, '#63D297');
        gradient.addColorStop(1, '#3BA55C');
        ctx.fillStyle = gradient;

        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
        x += barWidth + 1;
      }
    };

    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
      audioContext.close();
    };
  }, [stream, isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={200}
      height={40}
      className="rounded-lg bg-ink-900/50"
    />
  );
}
```

## Non-Functional Requirements

### NFR-1: Browser Compatibility

- Chrome 74+, Firefox 66+, Safari 14.1+, Edge 79+
- Fallback message for unsupported browsers
- Handle MediaRecorder API variations

### NFR-2: Performance

- Audio compressed to ~32kbps for efficient upload
- Max recording size: ~2MB for 2 minutes
- Transcription timeout: 60 seconds
- Immediate feedback on button states

### NFR-3: Accessibility

- ARIA labels for all states
- Visual indicators for recording/processing
- Keyboard accessible (Space to start/stop)
- Screen reader announcements for state changes

### NFR-4: Privacy

- Audio not stored permanently
- Transcription via secure proxy
- Clear recording state indicators
- Cancel option during recording

## Environment Variables

```bash
# Frontend (public)
NEXT_PUBLIC_ENABLE_VOICE_INPUT=true

# Gateway (server-side)
CHUTES_API_KEY=cpk_your_chutes_api_key
```

## Acceptance Criteria

- [ ] Microphone button starts recording on click
- [ ] Visual feedback during recording (red pulse, timer)
- [ ] Stop button ends recording
- [ ] Audio automatically transcribed on stop
- [ ] Transcribed text appended to input field
- [ ] Error handling for permission denied
- [ ] Error handling for transcription failure
- [ ] Works in Chrome, Firefox, Safari, Edge
- [ ] Max 2 minute recording limit
- [ ] Gateway proxy protects API key
- [ ] Tests for recording hook
- [ ] Tests for transcription service

## Files to Modify/Create

```
ui/
├── src/
│   ├── hooks/
│   │   └── useAudioRecorder.ts       # NEW - Recording hook
│   ├── lib/
│   │   └── transcription.ts          # NEW - Transcription client
│   └── components/
│       ├── ChatInput.tsx             # MODIFY - Integrate voice input
│       ├── VoiceInputButton.tsx      # NEW - Voice button component
│       ├── AudioWaveform.tsx         # NEW - Optional waveform viz
│       └── MicrophonePermissionDialog.tsx  # NEW - Permission UI

gateway/
└── janus_gateway/
    ├── routers/
    │   ├── __init__.py               # MODIFY - Include transcription router
    │   └── transcription.py          # NEW - Proxy endpoint
    └── config.py                     # MODIFY - Add chutes_api_key
```

## Open Questions

1. **Push-to-talk vs toggle**: Should holding mic button record, or click-to-start/click-to-stop?
2. **Language selection**: Should users be able to choose transcription language?
3. **Audio playback**: Should users be able to preview recording before sending?
4. **Continuous mode**: Support for longer dictation sessions with auto-send?

## Related Specs

- `specs/11_chat_ui.md` - Original chat UI spec
- `specs/37_extended_file_attachments.md` - File handling patterns
- `specs/competition/05_architecture_overview.md` - Platform services

NR_OF_TRIES: 1
