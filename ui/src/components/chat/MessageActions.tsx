'use client';

import { useState } from 'react';
import { Check, Copy, RefreshCw, Share2 } from 'lucide-react';

interface MessageActionsProps {
  textToCopy: string;
  onRegenerate?: () => void;
  onShare?: () => void;
  disabled?: boolean;
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

export function MessageActions({ textToCopy, onRegenerate, onShare, disabled = false }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const hasCopyText = Boolean(textToCopy.trim());

  const handleCopy = async () => {
    if (!hasCopyText) return;
    await copyText(textToCopy);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="message-actions">
      <button
        type="button"
        onClick={handleCopy}
        className="message-action-btn"
        title={hasCopyText ? 'Copy to clipboard' : 'Nothing to copy'}
        aria-label="Copy to clipboard"
        disabled={!hasCopyText || disabled}
      >
        {copied ? <Check size={14} className="text-moss" /> : <Copy size={14} />}
      </button>

      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          className="message-action-btn"
          title="Regenerate response"
          aria-label="Regenerate response"
          disabled={disabled}
        >
          <RefreshCw size={14} />
        </button>
      )}

      {onShare && (
        <button
          type="button"
          onClick={onShare}
          className="message-action-btn"
          title="Share conversation"
          aria-label="Share conversation"
          disabled={disabled}
        >
          <Share2 size={14} />
        </button>
      )}
    </div>
  );
}
