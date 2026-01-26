'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { DEFAULT_VOICE, generateSpeech, VOICES } from '@/lib/tts';
import { useSettingsStore } from '@/store/settings';

interface TTSPlayerProps {
  text: string;
  className?: string;
  autoPlay?: boolean;
  onAutoPlayHandled?: () => void;
}

type PlaybackState = 'idle' | 'loading' | 'playing' | 'paused';

export function TTSPlayer({
  text,
  className = '',
  autoPlay = false,
  onAutoPlayHandled,
}: TTSPlayerProps) {
  const [state, setState] = useState<PlaybackState>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showVoiceMenu, setShowVoiceMenu] = useState(false);
  const [announcement, setAnnouncement] = useState('');

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioEventsRef = useRef<{
    timeupdate?: () => void;
    ended?: () => void;
    error?: () => void;
  } | null>(null);

  const voiceMenuRef = useRef<HTMLDivElement | null>(null);
  const voiceButtonRef = useRef<HTMLButtonElement | null>(null);
  const voiceMenuId = useId();

  const voice = useSettingsStore((state) => state.ttsVoice);
  const speed = useSettingsStore((state) => state.ttsSpeed);
  const setTTSVoice = useSettingsStore((state) => state.setTTSVoice);

  const hasText = text.trim().length > 0;
  const isVoiceValid = VOICES.some((item) => item.id === voice);
  const selectedVoice = VOICES.find((item) => item.id === voice) ?? VOICES[0];

  useEffect(() => {
    if (!isVoiceValid) {
      setTTSVoice(DEFAULT_VOICE);
    }
  }, [isVoiceValid, setTTSVoice]);

  const detachAudioEvents = () => {
    if (!audioRef.current || !audioEventsRef.current) {
      return;
    }
    const { timeupdate, ended, error } = audioEventsRef.current;
    if (timeupdate) {
      audioRef.current.removeEventListener('timeupdate', timeupdate);
    }
    if (ended) {
      audioRef.current.removeEventListener('ended', ended);
    }
    if (error) {
      audioRef.current.removeEventListener('error', error);
    }
    audioEventsRef.current = null;
  };

  const cleanupAudio = () => {
    if (audioRef.current) {
      detachAudioEvents();
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, []);

  useEffect(() => {
    if (!showVoiceMenu) {
      return;
    }

    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (voiceMenuRef.current?.contains(target) || voiceButtonRef.current?.contains(target)) {
        return;
      }
      setShowVoiceMenu(false);
    };

    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowVoiceMenu(false);
        voiceButtonRef.current?.focus();
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('keydown', handleKeydown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeydown);
    };
  }, [showVoiceMenu]);

  const handlePlay = async () => {
    if (!hasText || state === 'loading') {
      return;
    }

    setError(null);

    if (audioRef.current && state === 'paused') {
      try {
        await audioRef.current.play();
        setState('playing');
        setAnnouncement('Playback resumed');
      } catch {
        setError('Playback failed');
        setState('idle');
        setAnnouncement('Playback failed');
      }
      return;
    }

    setState('loading');
    setAnnouncement('Loading audio');
    setProgress(0);
    cleanupAudio();

    try {
      const audioUrl = await generateSpeech(text, selectedVoice.id, speed);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      const handleTimeUpdate = () => {
        if (!audio.duration) {
          return;
        }
        const pct = (audio.currentTime / audio.duration) * 100;
        if (!Number.isNaN(pct)) {
          setProgress(pct);
        }
      };

      const handleEnded = () => {
        setState('idle');
        setProgress(0);
        setAnnouncement('Playback finished');
      };

      const handleAudioError = () => {
        setError('Playback failed');
        setState('idle');
        setAnnouncement('Playback failed');
      };

      audioEventsRef.current = {
        timeupdate: handleTimeUpdate,
        ended: handleEnded,
        error: handleAudioError,
      };

      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('ended', handleEnded);
      audio.addEventListener('error', handleAudioError);

      await audio.play();
      setState('playing');
      setAnnouncement('Playback started');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'TTS failed');
      setState('idle');
      setAnnouncement('Playback failed');
    }
  };

  useEffect(() => {
    if (!autoPlay || !hasText) return;
    if (state !== 'idle') return;

    let cancelled = false;
    handlePlay().finally(() => {
      if (!cancelled) {
        onAutoPlayHandled?.();
      }
    });

    return () => {
      cancelled = true;
    };
  }, [autoPlay, handlePlay, hasText, onAutoPlayHandled, state]);

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setState('paused');
      setAnnouncement('Playback paused');
    }
  };

  const handleStop = () => {
    cleanupAudio();
    setState('idle');
    setProgress(0);
    setAnnouncement('Playback stopped');
  };

  return (
    <div className={`tts-player ${className}`}>
      <div className="tts-controls">
        {state === 'playing' ? (
          <button
            type="button"
            onClick={handlePause}
            className="tts-btn tts-btn-pause"
            title="Pause"
            aria-label="Pause playback"
          >
            <PauseIcon />
          </button>
        ) : (
          <button
            type="button"
            onClick={handlePlay}
            className="tts-btn tts-btn-play"
            disabled={state === 'loading' || !hasText}
            title="Read Aloud"
            aria-label="Read aloud"
          >
            {state === 'loading' ? <SpinnerIcon /> : <PlayIcon />}
          </button>
        )}

        {(state === 'playing' || state === 'paused') && (
          <button
            type="button"
            onClick={handleStop}
            className="tts-btn tts-btn-stop"
            title="Stop"
            aria-label="Stop playback"
          >
            <StopIcon />
          </button>
        )}

        <div className="tts-voice-selector">
          <button
            ref={voiceButtonRef}
            type="button"
            onClick={() => setShowVoiceMenu((open) => !open)}
            className="tts-voice-btn"
            title="Select Voice"
            aria-label="Select voice"
            aria-expanded={showVoiceMenu}
            aria-controls={voiceMenuId}
            aria-haspopup="listbox"
          >
            <VoiceIcon />
            <span className="tts-voice-name">{selectedVoice?.name}</span>
          </button>

          {showVoiceMenu && (
            <div
              ref={voiceMenuRef}
              id={voiceMenuId}
              className="tts-voice-menu"
              role="listbox"
            >
              {VOICES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setTTSVoice(item.id);
                    setShowVoiceMenu(false);
                    if (audioRef.current) {
                      handleStop();
                    }
                  }}
                  className={`tts-voice-option ${item.id === voice ? 'active' : ''}`}
                  aria-label={`Select ${item.name} voice`}
                  aria-selected={item.id === voice}
                  role="option"
                >
                  <span>{item.name}</span>
                  <span className="tts-voice-meta">
                    {item.gender === 'female' ? 'F' : 'M'} / {item.accent}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {(state === 'playing' || state === 'paused') && (
        <div
          className="tts-progress"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress)}
        >
          <div className="tts-progress-bar" style={{ width: `${progress}%` }} />
        </div>
      )}

      {error && (
        <div className="tts-error" role="alert">
          {error}
        </div>
      )}

      <span className="sr-only" aria-live="polite">
        {announcement}
      </span>
    </div>
  );
}

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
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      <circle cx="9" cy="7" r="4" />
      <path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
      <path d="M17 8l2 2-2 2" />
      <path d="M20 6l2 2-2 2" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="w-4 h-4 animate-spin"
    >
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}
