'use client';

import { useState } from 'react';
import type { MessageMetadata } from '@/types/chat';

interface MessageFooterProps {
  metadata?: MessageMetadata;
  debugEnabled?: boolean;
}

function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'absolute';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
  return Promise.resolve();
}

export function MessageFooter({ metadata, debugEnabled = false }: MessageFooterProps) {
  const [showDebug, setShowDebug] = useState(false);

  if (!debugEnabled || !metadata) return null;

  const { requestId, model, durationMs } = metadata;
  const hasMeta = Boolean(model || durationMs !== undefined || requestId);
  if (!hasMeta) return null;

  const durationLabel =
    typeof durationMs === 'number' && Number.isFinite(durationMs)
      ? `${Math.round(durationMs)}ms`
      : null;

  return (
    <div className="message-footer">
      <div className="message-footer-row">
        <div className="message-footer-meta">
          {model && <span>{model}</span>}
          {durationLabel && <span>{model ? ' · ' : ''}{durationLabel}</span>}
        </div>
        {requestId && (
          <button
            type="button"
            onClick={() => setShowDebug(!showDebug)}
            className="message-footer-toggle"
            aria-expanded={showDebug}
          >
            {showDebug ? '▼ Debug' : '▶ Debug'}
          </button>
        )}
      </div>
      {showDebug && requestId && (
        <div className="message-footer-debug">
          <span className="message-footer-label">Request ID:</span>
          <span className="message-footer-value">{requestId}</span>
          <button
            type="button"
            onClick={() => copyText(requestId)}
            className="message-footer-copy"
            title="Copy request ID"
            aria-label="Copy request ID"
          >
            Copy
          </button>
        </div>
      )}
    </div>
  );
}
