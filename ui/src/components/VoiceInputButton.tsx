'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { transcribeViaGateway } from '@/lib/transcription';

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

  const handleTranscription = useCallback(
    async (blob: Blob) => {
      setIsTranscribing(true);
      setTranscriptionError(null);
      try {
        const result = await transcribeViaGateway(blob);
        const text = result.text?.trim();
        if (text) {
          onTranscription(text);
        }
      } catch (err) {
        setTranscriptionError('Transcription failed. Try again.');
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
    if (disabled || isTranscribing) return;

    if (isRecording) {
      stopRecording();
    } else {
      setTranscriptionError(null);
      startRecording();
    }
  }, [disabled, isTranscribing, isRecording, startRecording, stopRecording]);

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

    return [base, isRecording ? recording : idle, className].filter(Boolean).join(' ');
  }, [className, isRecording]);

  const statusMessage = error
    ? error
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
        disabled={disabled || isTranscribing}
        className={buttonClasses}
        aria-label={
          isRecording
            ? 'Stop recording'
            : isTranscribing
            ? 'Transcribing voice input'
            : 'Start voice input'
        }
        title={
          isRecording
            ? 'Stop recording'
            : isTranscribing
            ? 'Transcribing...'
            : 'Start voice input'
        }
      >
        {isTranscribing ? <SpinnerIcon /> : isRecording ? <StopIcon /> : <MicIcon />}
      </button>

      {isRecording && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 rounded bg-red-500/20 px-2 py-1 text-xs font-mono text-red-400 whitespace-nowrap">
          {formatDuration(duration)} · Esc to cancel
        </div>
      )}

      {error && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 rounded bg-red-500/90 px-2 py-1 text-xs text-white whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
}
