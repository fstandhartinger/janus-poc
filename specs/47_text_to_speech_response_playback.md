# Spec 47: Text-to-Speech Response Playback

## Status: COMPLETE

## Context / Why

Users may prefer to listen to AI responses rather than read them. This is especially useful for:

- Long responses that would take time to read
- Multitasking while getting information
- Accessibility for visually impaired users
- Mobile usage where reading is inconvenient

This spec adds TTS playback using the Chutes Kokoro TTS API.

## Goals

- Add "Read Aloud" button to assistant messages
- Provide voice selection dropdown
- Support play/pause/stop controls
- Show playback progress indicator
- Cache generated audio for replay

## Non-Goals

- Real-time streaming TTS during generation
- Voice cloning
- Multi-language support (future)

## Functional Requirements

### FR-1: TTS Service

```typescript
// ui/src/lib/tts.ts

export interface TTSVoice {
  id: string;
  name: string;
  gender: 'male' | 'female';
  accent: 'american' | 'british';
}

export const VOICES: TTSVoice[] = [
  { id: 'af_sky', name: 'Sky', gender: 'female', accent: 'american' },
  { id: 'af_bella', name: 'Bella', gender: 'female', accent: 'american' },
  { id: 'af_sarah', name: 'Sarah', gender: 'female', accent: 'american' },
  { id: 'af_nicole', name: 'Nicole', gender: 'female', accent: 'american' },
  { id: 'am_adam', name: 'Adam', gender: 'male', accent: 'american' },
  { id: 'am_michael', name: 'Michael', gender: 'male', accent: 'american' },
  { id: 'bf_emma', name: 'Emma', gender: 'female', accent: 'british' },
  { id: 'bf_isabella', name: 'Isabella', gender: 'female', accent: 'british' },
  { id: 'bm_george', name: 'George', gender: 'male', accent: 'british' },
  { id: 'bm_lewis', name: 'Lewis', gender: 'male', accent: 'british' },
];

export const DEFAULT_VOICE = 'af_sky';

const TTS_ENDPOINT = 'https://chutes-kokoro.chutes.ai/speak';

// Audio cache to avoid re-generating
const audioCache = new Map<string, string>();

function getCacheKey(text: string, voice: string): string {
  // Hash the text for cache key
  const hash = text.slice(0, 100) + text.length + voice;
  return btoa(hash).slice(0, 32);
}

export async function generateSpeech(
  text: string,
  voice: string = DEFAULT_VOICE,
  speed: number = 1.0
): Promise<string> {
  const cacheKey = getCacheKey(text, voice);

  // Return cached audio URL if available
  if (audioCache.has(cacheKey)) {
    return audioCache.get(cacheKey)!;
  }

  // Strip markdown formatting for cleaner speech
  const cleanText = stripMarkdown(text);

  const response = await fetch(TTS_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: cleanText,
      voice,
      speed,
    }),
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.statusText}`);
  }

  // Convert audio buffer to blob URL
  const audioBuffer = await response.arrayBuffer();
  const blob = new Blob([audioBuffer], { type: 'audio/wav' });
  const audioUrl = URL.createObjectURL(blob);

  // Cache for replay
  audioCache.set(cacheKey, audioUrl);

  return audioUrl;
}

function stripMarkdown(text: string): string {
  return text
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, 'code block')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove links but keep text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove images
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, 'image: $1')
    // Remove bold/italic
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove horizontal rules
    .replace(/^[-*_]{3,}$/gm, '')
    // Remove list markers
    .replace(/^[\s]*[-*+]\s+/gm, '')
    .replace(/^[\s]*\d+\.\s+/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function clearAudioCache(): void {
  // Revoke all blob URLs to free memory
  audioCache.forEach((url) => URL.revokeObjectURL(url));
  audioCache.clear();
}
```

### FR-2: TTS Audio Player Component

```tsx
// ui/src/components/TTSPlayer.tsx

'use client';

import { useState, useRef, useEffect } from 'react';
import { generateSpeech, VOICES, DEFAULT_VOICE, type TTSVoice } from '@/lib/tts';

interface TTSPlayerProps {
  text: string;
  className?: string;
}

type PlaybackState = 'idle' | 'loading' | 'playing' | 'paused';

export function TTSPlayer({ text, className = '' }: TTSPlayerProps) {
  const [state, setState] = useState<PlaybackState>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [voice, setVoice] = useState<string>(DEFAULT_VOICE);
  const [showVoiceMenu, setShowVoiceMenu] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlay = async () => {
    setError(null);

    // If we have audio and it's paused, resume
    if (audioRef.current && state === 'paused') {
      audioRef.current.play();
      setState('playing');
      return;
    }

    // Generate new audio
    setState('loading');

    try {
      const audioUrl = await generateSpeech(text, voice);
      audioUrlRef.current = audioUrl;

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.addEventListener('timeupdate', () => {
        const pct = (audio.currentTime / audio.duration) * 100;
        setProgress(pct);
      });

      audio.addEventListener('ended', () => {
        setState('idle');
        setProgress(0);
      });

      audio.addEventListener('error', () => {
        setError('Playback failed');
        setState('idle');
      });

      await audio.play();
      setState('playing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'TTS failed');
      setState('idle');
    }
  };

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setState('paused');
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setState('idle');
      setProgress(0);
    }
  };

  const selectedVoice = VOICES.find((v) => v.id === voice);

  return (
    <div className={`tts-player ${className}`}>
      <div className="tts-controls">
        {/* Play/Pause Button */}
        {state === 'playing' ? (
          <button
            onClick={handlePause}
            className="tts-btn tts-btn-pause"
            title="Pause"
          >
            <PauseIcon />
          </button>
        ) : (
          <button
            onClick={handlePlay}
            className="tts-btn tts-btn-play"
            disabled={state === 'loading'}
            title="Read Aloud"
          >
            {state === 'loading' ? <SpinnerIcon /> : <PlayIcon />}
          </button>
        )}

        {/* Stop Button (visible when playing/paused) */}
        {(state === 'playing' || state === 'paused') && (
          <button
            onClick={handleStop}
            className="tts-btn tts-btn-stop"
            title="Stop"
          >
            <StopIcon />
          </button>
        )}

        {/* Voice Selector */}
        <div className="tts-voice-selector">
          <button
            onClick={() => setShowVoiceMenu(!showVoiceMenu)}
            className="tts-voice-btn"
            title="Select Voice"
          >
            <VoiceIcon />
            <span className="tts-voice-name">{selectedVoice?.name}</span>
          </button>

          {showVoiceMenu && (
            <div className="tts-voice-menu">
              {VOICES.map((v) => (
                <button
                  key={v.id}
                  onClick={() => {
                    setVoice(v.id);
                    setShowVoiceMenu(false);
                    // Reset audio if voice changed
                    if (audioRef.current) {
                      handleStop();
                    }
                  }}
                  className={`tts-voice-option ${v.id === voice ? 'active' : ''}`}
                >
                  <span>{v.name}</span>
                  <span className="tts-voice-meta">
                    {v.gender === 'female' ? 'F' : 'M'} / {v.accent}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {(state === 'playing' || state === 'paused') && (
        <div className="tts-progress">
          <div
            className="tts-progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Error Message */}
      {error && <div className="tts-error">{error}</div>}
    </div>
  );
}

// Icons

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path d="M6 6h12v12H6z" />
    </svg>
  );
}

function VoiceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 animate-spin">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}
```

### FR-3: Integration with MessageBubble

```tsx
// ui/src/components/MessageBubble.tsx

import { TTSPlayer } from './TTSPlayer';

// Add to assistant message render:

{message.role === 'assistant' && message.content && (
  <div className="message-actions">
    <TTSPlayer
      text={typeof message.content === 'string' ? message.content : ''}
      className="mt-2"
    />
    {/* Copy button, etc. */}
  </div>
)}
```

### FR-4: TTS Styles

```css
/* ui/src/app/globals.css */

/* TTS Player */
.tts-player {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tts-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tts-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.tts-btn:hover:not(:disabled) {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.tts-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tts-btn-play:hover:not(:disabled) {
  color: var(--accent-green);
  border-color: var(--accent-green);
}

.tts-btn-stop:hover {
  color: var(--accent-red);
  border-color: var(--accent-red);
}

.tts-voice-selector {
  position: relative;
}

.tts-voice-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.tts-voice-btn:hover {
  background: var(--card-bg-hover);
}

.tts-voice-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.25rem;
  min-width: 160px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  box-shadow: var(--shadow-lg);
  z-index: 50;
  overflow: hidden;
}

.tts-voice-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
}

.tts-voice-option:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.tts-voice-option.active {
  color: var(--accent-green);
}

.tts-voice-meta {
  opacity: 0.6;
  font-size: 0.625rem;
  text-transform: uppercase;
}

.tts-progress {
  height: 3px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}

.tts-progress-bar {
  height: 100%;
  background: var(--accent-green);
  transition: width 0.1s linear;
}

.tts-error {
  font-size: 0.75rem;
  color: var(--accent-red);
}
```

### FR-5: User Preferences (Optional)

```typescript
// ui/src/store/settings.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  ttsVoice: string;
  ttsSpeed: number;
  ttsAutoPlay: boolean;
  setTTSVoice: (voice: string) => void;
  setTTSSpeed: (speed: number) => void;
  setTTSAutoPlay: (autoPlay: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ttsVoice: 'af_sky',
      ttsSpeed: 1.0,
      ttsAutoPlay: false,
      setTTSVoice: (voice) => set({ ttsVoice: voice }),
      setTTSSpeed: (speed) => set({ ttsSpeed: speed }),
      setTTSAutoPlay: (autoPlay) => set({ ttsAutoPlay: autoPlay }),
    }),
    {
      name: 'janus-settings',
    }
  )
);
```

## Non-Functional Requirements

### NFR-1: Performance

- TTS generation < 3 seconds for typical responses
- Audio caching to avoid re-generation
- Memory cleanup for blob URLs

### NFR-2: Accessibility

- Keyboard accessible controls
- ARIA labels on all buttons
- Screen reader announcements for state changes

### NFR-3: Mobile

- Touch-friendly control sizes (min 44px)
- Works with device audio output
- Respects system mute state

## Acceptance Criteria

- [ ] "Read Aloud" button visible on assistant messages
- [ ] Play/Pause/Stop controls working
- [ ] Voice selection dropdown working
- [ ] Progress bar shows playback position
- [ ] Audio cached for replay
- [ ] Markdown stripped from speech text
- [ ] Error states handled gracefully
- [ ] Mobile-friendly layout

## Files to Modify/Create

```
ui/
└── src/
    ├── lib/
    │   └── tts.ts                # NEW - TTS service
    ├── components/
    │   ├── TTSPlayer.tsx         # NEW - TTS player component
    │   └── MessageBubble.tsx     # MODIFY - Add TTS player
    ├── store/
    │   └── settings.ts           # NEW - User settings
    └── app/
        └── globals.css           # MODIFY - TTS styles
```

## Dependencies

None (uses native Audio API)

## Related Specs

- `specs/39_speech_to_text_voice_input.md` - Voice input (opposite direction)
- `specs/11_chat_ui.md` - Chat UI integration

NR_OF_TRIES: 1
