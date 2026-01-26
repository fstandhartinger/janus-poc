'use client';
import { useEffect, useRef, useState } from 'react';
import type { Message } from '@/types/chat';
import { stripCanvasBlocks } from '@/lib/canvas-parser';
import { parseAudioContent } from '@/lib/audio-parser';
import { MarkdownContent } from '@/lib/markdown-renderer';
import { MediaRenderer } from './MediaRenderer';
import { TTSPlayer } from './TTSPlayer';
import { AudioResponse } from './audio/AudioResponse';
import { MessageActions } from './chat/MessageActions';
import { ThinkingIndicator } from './ThinkingIndicator';

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
  isStreaming?: boolean;
  autoPlay?: boolean;
  onAutoPlayHandled?: () => void;
  onRegenerate?: () => void;
  onShare?: () => void;
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

function useStreamingBuffer(content: string, isStreaming: boolean) {
  const [displayContent, setDisplayContent] = useState(content);
  const bufferRef = useRef(content);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!isStreaming) {
      setDisplayContent(content);
      bufferRef.current = content;
      return;
    }

    bufferRef.current = content;

    const updateDisplay = () => {
      if (bufferRef.current !== displayContent) {
        setDisplayContent(bufferRef.current);
      }
      rafRef.current = requestAnimationFrame(updateDisplay);
    };

    rafRef.current = requestAnimationFrame(updateDisplay);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [content, displayContent, isStreaming]);

  return displayContent;
}

const USELESS_REASONING_PATTERNS = [
  /^processing(\s*request)?(\.{2,})?$/i,
  /^thinking(\.{2,})?$/i,
  /^working(\.{2,})?$/i,
  /^loading(\.{2,})?$/i,
];

function isUsefulReasoning(content?: string): boolean {
  if (!content) return false;
  const trimmed = content.trim();
  if (trimmed.length < 20) return false;
  return !USELESS_REASONING_PATTERNS.some((pattern) => pattern.test(trimmed));
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

export function MessageBubble({
  message,
  showReasoning,
  isStreaming = false,
  autoPlay = false,
  onAutoPlayHandled,
  onRegenerate,
  onShare,
}: MessageBubbleProps) {
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
  const hasAudio = parsedAudio.length > 0;

  // Strip ANSI codes from reasoning content
  const cleanedReasoning = stripAnsiCodes(message.reasoning_content || '');
  const hasUsefulReasoning = showReasoning && isUsefulReasoning(cleanedReasoning);
  const hasRichContent =
    Array.isArray(message.content) && message.content.some((part) => part.type !== 'text');
  const hasArtifacts = Boolean(message.artifacts?.length);
  const shouldShowPlaceholder =
    !isUser &&
    isStreaming &&
    !hasText &&
    !hasAudio &&
    !hasUsefulReasoning &&
    !hasRichContent &&
    !hasArtifacts;
  const hasRenderableContent =
    hasText || hasAudio || hasUsefulReasoning || hasRichContent || hasArtifacts || shouldShowPlaceholder;
  const displayText = useStreamingBuffer(cleanedText, isStreaming && !isUser);
  const canShowActions = hasRenderableContent && !shouldShowPlaceholder;

  // Auto-collapse thinking when actual content starts streaming
  // Start expanded (true), then collapse when content arrives
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(!hasText);

  // Auto-collapse when content starts appearing
  useEffect(() => {
    if (!hasUsefulReasoning) {
      return;
    }
    if (hasText && isThinkingExpanded) {
      setIsThinkingExpanded(false);
    }
  }, [hasText, hasUsefulReasoning, isThinkingExpanded]);

  if (!hasRenderableContent) {
    return null;
  }

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}
      data-testid={isUser ? 'user-message' : 'assistant-message'}
    >
      <div
        className={`chat-message max-w-[80%] ${
          isUser ? 'chat-message-user' : 'chat-message-assistant'
        }${isStreaming && !isUser ? ' chat-message-streaming' : ''}`}
      >
        <MediaRenderer content={message.content} />

        {/* Show reasoning panel if available - collapsible with max-height */}
        {hasUsefulReasoning && (
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

        <ThinkingIndicator
          isVisible={!isUser && shouldShowPlaceholder}
        />

        {/* Message content */}
        {hasText && (
          <div className={isStreaming && !isUser ? 'streaming-content' : undefined}>
            <MarkdownContent content={displayText} />
          </div>
        )}

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
          <div className="message-tts">
            <TTSPlayer
              text={cleanedText}
              className="mt-2"
              autoPlay={autoPlay}
              onAutoPlayHandled={onAutoPlayHandled}
            />
          </div>
        )}

        {isStreaming && !isUser && (
          <div className="streaming-indicator mt-3 flex items-center gap-2 text-xs text-gray-400">
            <span className="streaming-dots">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
            <span>Generating...</span>
          </div>
        )}

        {canShowActions && (
          <div className="message-action-bar">
            <MessageActions
              textToCopy={cleanedText}
              onRegenerate={onRegenerate}
              onShare={onShare}
              disabled={isStreaming}
            />
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
