'use client';
import { useState, useEffect } from 'react';
import type { Message } from '@/types/chat';
import { stripCanvasBlocks } from '@/lib/canvas-parser';
import { parseAudioContent } from '@/lib/audio-parser';
import { MarkdownContent } from '@/lib/markdown-renderer';
import { MediaRenderer } from './MediaRenderer';
import { TTSPlayer } from './TTSPlayer';
import { AudioResponse } from './audio/AudioResponse';

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
}

/**
 * Strip ANSI escape codes from text.
 * Handles sequences like [1;31m, [0m, etc.
 */
function stripAnsiCodes(text: string): string {
  if (!text) return text;
  // Match ANSI escape sequences: ESC[ followed by params and command letter
  // Also handle the literal bracket notation [1;31m that appears in some outputs
  return text
    .replace(/\x1b\[[0-9;]*m/g, '') // Standard ANSI: ESC[...m (hex)
    .replace(/\u001b\[[0-9;]*m/g, '') // Unicode ESC
    .replace(/\[([0-9;]*)m/g, ''); // Literal bracket notation [1;31m
}

const AUDIO_BLOCK_REGEX = /:::audio\[([^\]]*)\]\s*\r?\n(data:audio\/[^;]+;base64,[A-Za-z0-9+/=]+)\s*\r?\n:::/g;
const INLINE_AUDIO_REGEX = /data:audio\/(wav|mp3|ogg);base64,[A-Za-z0-9+/=]+/g;

function stripAudioContent(content: string) {
  if (!content) {
    return content;
  }

  return content
    .replace(AUDIO_BLOCK_REGEX, '')
    .replace(INLINE_AUDIO_REGEX, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function normalizeAudioMetadata(metadata?: Record<string, unknown>) {
  if (!metadata) {
    return undefined;
  }

  const voice = typeof metadata.voice === 'string' ? metadata.voice : undefined;
  const style = typeof metadata.style === 'string' ? metadata.style : undefined;
  const duration = normalizeDuration(metadata.duration);
  const hasVocals = normalizeBoolean(metadata.hasVocals ?? metadata['has_vocals']);

  if (!voice && !style && duration === undefined && hasVocals === undefined) {
    return undefined;
  }

  return {
    voice,
    style,
    duration,
    hasVocals,
  };
}

function normalizeDuration(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return undefined;
}

function normalizeBoolean(value: unknown): boolean | undefined {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    if (value.toLowerCase() === 'true') {
      return true;
    }
    if (value.toLowerCase() === 'false') {
      return false;
    }
  }
  return undefined;
}

export function MessageBubble({ message, showReasoning }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const contentParts = typeof message.content === 'string' ? [] : message.content || [];
  const rawTextContent =
    typeof message.content === 'string'
      ? message.content
      : contentParts
          .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
          .map((c) => c.text)
          .join('\n');
  const textContent = stripCanvasBlocks(rawTextContent);
  const parsedAudio = parseAudioContent(textContent);
  const cleanedText = stripAudioContent(textContent);
  const hasText = Boolean(cleanedText);

  // Strip ANSI codes from reasoning content
  const cleanedReasoning = stripAnsiCodes(message.reasoning_content || '');

  // Auto-collapse thinking when actual content starts streaming
  // Start expanded (true), then collapse when content arrives
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(!hasText);

  // Auto-collapse when content starts appearing
  useEffect(() => {
    if (hasText && isThinkingExpanded) {
      setIsThinkingExpanded(false);
    }
  }, [hasText]);

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      data-testid={isUser ? 'user-message' : 'assistant-message'}
    >
      <div
        className={`chat-message max-w-[80%] ${
          isUser ? 'chat-message-user' : 'chat-message-assistant'
        }`}
      >
        <MediaRenderer content={message.content} />

        {/* Show reasoning panel if available - collapsible with max-height */}
        {showReasoning && cleanedReasoning && (
          <div className="mb-3 rounded-lg text-sm border border-[#1F2937] bg-[#111726]/70 overflow-hidden">
            <button
              type="button"
              onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
              className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors cursor-pointer"
            >
              <div className="text-[11px] uppercase tracking-[0.2em] text-[#F59E0B] font-semibold">
                Thinking
              </div>
              <svg
                className={`w-4 h-4 text-[#F59E0B] transition-transform duration-200 ${isThinkingExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {isThinkingExpanded && (
              <div className="px-3 pb-3 max-h-48 overflow-y-auto scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent">
                <div className="text-[#D1D5DB] whitespace-pre-wrap text-xs leading-relaxed">
                  {cleanedReasoning}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Message content */}
        {hasText && <MarkdownContent content={cleanedText} />}

        {parsedAudio.length > 0 && (
          <div className="mt-3 space-y-2">
            {parsedAudio.map((audio, index) => (
              <AudioResponse
                key={`${message.id}-audio-${index}`}
                audioUrl={audio.url}
                type={audio.type}
                title={audio.title ?? (parsedAudio.length > 1 ? `Audio ${index + 1}` : undefined)}
                metadata={normalizeAudioMetadata(audio.metadata)}
              />
            ))}
          </div>
        )}

        {!isUser && hasText && (
          <div className="message-actions">
            <TTSPlayer text={cleanedText} className="mt-2" />
          </div>
        )}

        {/* Show artifacts */}
        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.artifacts.map((artifact) => (
              <a
                key={artifact.id}
                href={artifact.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 p-2 bg-white/5 rounded-lg text-sm hover:bg-white/10 transition-colors"
              >
                <span className="text-[#63D297]">Attachment</span>
                <span className="truncate">{artifact.display_name}</span>
                <span className="text-xs text-[#6B7280]">
                  ({Math.round(artifact.size_bytes / 1024)}KB)
                </span>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
