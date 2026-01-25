'use client';

import { useMemo, useState } from 'react';
import { AudioPlayer } from './AudioPlayer';

interface AudioResponseMetadata {
  voice?: string;
  style?: string;
  duration?: number;
  hasVocals?: boolean;
}

interface AudioResponseProps {
  audioUrl: string;
  type: 'speech' | 'music' | 'sound';
  title?: string;
  metadata?: AudioResponseMetadata;
}

export function AudioResponse({
  audioUrl,
  type,
  title,
  metadata,
}: AudioResponseProps) {
  const [expanded, setExpanded] = useState(false);

  const normalizedMetadata = useMemo(() => normalizeMetadata(metadata), [metadata]);
  const hasMetadata = Boolean(
    normalizedMetadata.voice || normalizedMetadata.style || normalizedMetadata.duration,
  );

  const typeLabel = useMemo(() => {
    if (type === 'music') {
      return normalizedMetadata.hasVocals ? 'Song' : 'Music';
    }
    if (type === 'speech') {
      return 'Speech';
    }
    return 'Sound';
  }, [normalizedMetadata.hasVocals, type]);

  const iconLabel = useMemo(() => {
    switch (type) {
      case 'speech':
        return 'S';
      case 'music':
        return 'M';
      case 'sound':
        return 'FX';
      default:
        return 'A';
    }
  }, [type]);

  const downloadName = useMemo(() => {
    const extMatch = /^data:audio\/([^;]+);/i.exec(audioUrl);
    const ext = extMatch?.[1]?.toLowerCase() || 'wav';
    const safeExt = ext.includes('/') ? 'wav' : ext;
    const prefix = type === 'speech' ? 'speech' : type === 'music' ? 'music' : type === 'sound' ? 'sound' : 'audio';
    return `${prefix}.${safeExt}`;
  }, [audioUrl, type]);

  return (
    <div className={`audio-response audio-response-${type}`}>
      <div className="audio-response-header">
        <span className="audio-response-icon" aria-hidden="true">
          {iconLabel}
        </span>
        <span className="audio-response-type">{typeLabel}</span>
        {title && <span className="audio-response-title">{title}</span>}
        {hasMetadata && (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="audio-response-details-btn"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide details' : 'Details'}
          </button>
        )}
      </div>

      <AudioPlayer src={audioUrl} downloadName={downloadName} />

      {expanded && hasMetadata && (
        <div className="audio-response-metadata">
          {normalizedMetadata.voice && (
            <div className="metadata-item">
              <span className="metadata-label">Voice:</span>
              <span className="metadata-value">{normalizedMetadata.voice}</span>
            </div>
          )}
          {normalizedMetadata.style && (
            <div className="metadata-item">
              <span className="metadata-label">Style:</span>
              <span className="metadata-value">{normalizedMetadata.style}</span>
            </div>
          )}
          {normalizedMetadata.duration !== undefined && (
            <div className="metadata-item">
              <span className="metadata-label">Duration:</span>
              <span className="metadata-value">
                {formatDuration(normalizedMetadata.duration)}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function normalizeMetadata(metadata?: AudioResponseMetadata): AudioResponseMetadata {
  if (!metadata) {
    return {};
  }
  const duration = typeof metadata.duration === 'number' ? metadata.duration : undefined;

  return {
    voice: metadata.voice,
    style: metadata.style,
    duration: Number.isFinite(duration) ? duration : undefined,
    hasVocals: metadata.hasVocals === true,
  };
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '0:00';
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
