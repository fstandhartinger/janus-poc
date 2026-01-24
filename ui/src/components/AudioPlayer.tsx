'use client';

import type { MouseEvent } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';

interface AudioPlayerProps {
  src: string;
  title?: string;
  downloadName?: string;
  variant?: 'default' | 'music';
  className?: string;
}

export function AudioPlayer({
  src,
  title,
  downloadName = 'audio.wav',
  variant = 'default',
  className,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolvedDownloadName = useMemo(() => {
    if (downloadName) {
      return downloadName;
    }
    const match = /^data:audio\/([^;]+);/i.exec(src);
    if (match?.[1]) {
      return `audio.${match[1]}`;
    }
    return 'audio.wav';
  }, [downloadName, src]);

  useEffect(() => {
    setIsPlaying(false);
    setProgress(0);
    setDuration(0);
    setCurrentTime(0);
    setIsLoading(true);
    setError(null);
    if (audioRef.current) {
      audioRef.current.load();
    }
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      const nextDuration = audio.duration || 0;
      const nextTime = audio.currentTime || 0;
      setCurrentTime(nextTime);
      if (nextDuration > 0) {
        const pct = (nextTime / nextDuration) * 100;
        setProgress(Number.isFinite(pct) ? pct : 0);
      } else {
        setProgress(0);
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      setIsLoading(false);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    const handleWaiting = () => {
      setIsLoading(true);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
    };

    const handleError = () => {
      setIsPlaying(false);
      setIsLoading(false);
      setError('Audio failed to load.');
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('waiting', handleWaiting);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [src]);

  const togglePlay = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
      return;
    }

    try {
      await audio.play();
      setIsPlaying(true);
    } catch {
      setIsPlaying(false);
      setError('Unable to play audio.');
    }
  };

  const handleSeek = (event: MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audio.currentTime = Math.max(0, Math.min(audio.duration, percent * audio.duration));
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = resolvedDownloadName;
    link.rel = 'noopener';
    link.click();
  };

  const formatTime = (seconds: number) => {
    if (!Number.isFinite(seconds) || seconds <= 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={[
        'audio-player',
        variant === 'music' ? 'music-player' : '',
        className || '',
      ]
        .join(' ')
        .trim()}
      aria-busy={isLoading}
    >
      <audio ref={audioRef} src={src} preload="metadata" />

      {title && <div className="audio-title">{title}</div>}

      <div className="audio-controls">
        <button
          type="button"
          onClick={togglePlay}
          className="audio-play-btn"
          aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>

        <div className="audio-progress-container" onClick={handleSeek} role="button" tabIndex={0}>
          <div className="audio-progress-bar">
            <div
              className="audio-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          {isLoading && <div className="audio-loading">Loading audio...</div>}
        </div>

        <div className="audio-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        <button
          type="button"
          onClick={handleDownload}
          className="audio-download-btn"
          title="Download"
          aria-label="Download audio"
        >
          <DownloadIcon />
        </button>
      </div>

      {error && <div className="audio-error">{error}</div>}
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5" aria-hidden="true">
      <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </svg>
  );
}
