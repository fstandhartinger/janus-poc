'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Message, MessageContent } from '@/types/chat';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: string;
  messages: Message[];
}

const getMessageText = (content: MessageContent) => {
  if (typeof content === 'string') {
    return content;
  }
  return (content || [])
    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
    .map((part) => part.text)
    .join('\n');
};

function buildTranscript(messages: Message[]) {
  return messages
    .map((message) => {
      const text = getMessageText(message.content).trim();
      if (!text) {
        return `${message.role.toUpperCase()}: [non-text content]`;
      }
      return `${message.role.toUpperCase()}:\n${text}`;
    })
    .join('\n\n---\n\n');
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
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
}

export function ShareModal({ isOpen, onClose, conversationId, messages }: ShareModalProps) {
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const transcript = useMemo(() => buildTranscript(messages), [messages]);

  useEffect(() => {
    if (!isOpen) {
      setShareUrl('');
      setCopied(false);
      return;
    }

    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleGenerate = () => {
    const url = new URL('/chat', window.location.origin);
    url.searchParams.set('initial', transcript);
    url.searchParams.set('source', 'share');
    if (conversationId) {
      url.searchParams.set('conversation', conversationId);
    }
    setShareUrl(url.toString());
  };

  const handleCopyLink = async () => {
    if (!shareUrl) return;
    await copyText(shareUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyTranscript = async () => {
    await copyText(transcript);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Share conversation"
      onClick={onClose}
    >
      <div
        className="glass-card share-modal w-full max-w-lg p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="share-modal-header">
          <h2 className="share-modal-title">Share Conversation</h2>
          <button
            type="button"
            className="share-modal-close"
            onClick={onClose}
            aria-label="Close share dialog"
          >
            ✕
          </button>
        </div>

        <div className="share-modal-body">
          {!shareUrl ? (
            <button
              type="button"
              onClick={handleGenerate}
              className="share-modal-generate"
            >
              Generate Share Link
            </button>
          ) : (
            <div className="share-modal-link-row">
              <input value={shareUrl} readOnly className="share-modal-input" />
              <button type="button" onClick={handleCopyLink} className="share-modal-copy">
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleCopyTranscript}
            className="share-modal-secondary"
          >
            Copy as Plain Text
          </button>
        </div>
      </div>
    </div>
  );
}
