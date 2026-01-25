'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { TranscriptionFailedError, transcribeViaGateway, checkTranscriptionHealth } from '@/lib/transcription';

interface VoiceInputButtonProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

function formatDuration(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 11a7 7 0 0014 0" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v3" />
    </svg>
  );
}

function MicOffIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 11a7 7 0 0014 0" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v3" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3l18 18" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <rect x="7" y="7" width="10" height="10" rx="2" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 animate-spin" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}

export function VoiceInputButton({ onTranscription, disabled, className }: VoiceInputButtonProps) {
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
  const [voiceInputDisabled, setVoiceInputDisabled] = useState(false);
  const [errorSuggestion, setErrorSuggestion] = useState<string | null>(null);

  const {
    isRecording,
    duration,
    audioBlob,
    error: recordingError,
    startRecording,
    stopRecording,
    cancelRecording,
    reset,
  } = useAudioRecorder({ maxDuration: 120 });

  const error = transcriptionError || recordingError;

  // Check service health on mount
  useEffect(() => {
    void checkTranscriptionHealth().then((health) => {
      if (!health.available) {
        setVoiceInputDisabled(true);
      }
    });
  }, []);

  const handleTranscription = useCallback(
    async (blob: Blob) => {
      setIsTranscribing(true);
      setTranscriptionError(null);
      setErrorSuggestion(null);
      try {
        const result = await transcribeViaGateway(blob);
        const text = result.text?.trim();
        if (text) {
          onTranscription(text);
        }
      } catch (err) {
        console.error('Transcription error:', err);
        if (err instanceof TranscriptionFailedError) {
          setTranscriptionError(err.suggestion || err.message);
          setErrorSuggestion(err.suggestion || null);
          if (!err.recoverable) {
            setVoiceInputDisabled(true);
          }
        } else {
          setTranscriptionError('Voice input failed. Please type your message.');
        }
      } finally {
        setIsTranscribing(false);
        reset();
      }
    },
    [onTranscription, reset]
  );

  useEffect(() => {
    if (audioBlob && !isRecording && !isTranscribing) {
      void handleTranscription(audioBlob);
    }
  }, [audioBlob, isRecording, isTranscribing, handleTranscription]);

  const handleClick = useCallback(() => {
    if (disabled || isTranscribing || voiceInputDisabled) return;

    if (isRecording) {
      stopRecording();
    } else {
      setTranscriptionError(null);
      setErrorSuggestion(null);
      startRecording();
    }
  }, [disabled, isTranscribing, voiceInputDisabled, isRecording, startRecording, stopRecording]);

  useEffect(() => {
    if (!isRecording) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        cancelRecording();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isRecording, cancelRecording]);

  const buttonClasses = useMemo(() => {
    const base =
      'w-9 h-9 rounded-full border flex items-center justify-center transition-all disabled:opacity-50';
    const idle =
      'border-[#1F2937] text-[#9CA3AF] hover:text-[#F3F4F6] hover:border-[#374151]';
    const recording = 'bg-red-500/20 border-red-500 text-red-500 animate-pulse';
    const unavailable = 'border-[#374151] text-[#4B5563] cursor-not-allowed';

    return [
      base,
      voiceInputDisabled ? unavailable : isRecording ? recording : idle,
      className,
    ]
      .filter(Boolean)
      .join(' ');
  }, [className, isRecording, voiceInputDisabled]);

  const statusMessage = error
    ? error
    : voiceInputDisabled
    ? 'Voice input is temporarily unavailable'
    : isTranscribing
    ? 'Transcribing voice input'
    : isRecording
    ? 'Recording voice input'
    : 'Voice input ready';

  return (
    <div className="relative">
      <span className="sr-only" aria-live="polite">
        {statusMessage}
      </span>

      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isTranscribing || voiceInputDisabled}
        className={buttonClasses}
        aria-label={
          voiceInputDisabled
            ? 'Voice input unavailable'
            : isRecording
            ? 'Stop recording'
            : isTranscribing
            ? 'Transcribing voice input'
            : 'Start voice input'
        }
        title={
          voiceInputDisabled
            ? 'Voice input is temporarily unavailable'
            : isRecording
            ? 'Stop recording'
            : isTranscribing
            ? 'Transcribing...'
            : 'Start voice input'
        }
      >
        {voiceInputDisabled ? (
          <MicOffIcon />
        ) : isTranscribing ? (
          <SpinnerIcon />
        ) : isRecording ? (
          <StopIcon />
        ) : (
          <MicIcon />
        )}
      </button>

      {isRecording && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 rounded bg-red-500/20 px-2 py-1 text-xs font-mono text-red-400 whitespace-nowrap">
          {formatDuration(duration)} · Esc to cancel
        </div>
      )}

      {error && !voiceInputDisabled && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 rounded bg-red-500/90 px-2 py-1 text-xs text-white whitespace-nowrap">
          {error}
        </div>
      )}

      {voiceInputDisabled && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 rounded bg-yellow-600/90 px-2 py-1 text-xs text-white whitespace-nowrap">
          Voice input unavailable
        </div>
      )}
    </div>
  );
}
