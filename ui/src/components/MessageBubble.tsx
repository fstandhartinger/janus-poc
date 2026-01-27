'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Message, MessageContent } from '@/types/chat';
import { stripCanvasBlocks } from '@/lib/canvas-parser';
import { parseAudioContent } from '@/lib/audio-parser';
import { parseImageContent } from '@/lib/image-parser';
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

// Status messages that shouldn't trigger thinking collapse
const STATUS_MESSAGE_PATTERNS = [
  /^\[Agent\]/i,
  /^⏳/,
  /^🔄/,
  /^💭/,
  /^🔧/,
  /^\[Tool/i,
  /^\[Thinking/i,
  /^\[System/i,
  /^Heartbeat/i,
  /^\(no content\)/i,
  /^Using tool:/i,
  /^Starting/i,
  /^Sandbox created/i,
  /^Running/i,
  /^Agent working/i,
  /^Files changed/i,
  /^Tool output/i,
  /^Agent completed/i,
  /^Terminating sandbox/i,
  /^Uploading/i,
  /^Selecting/i,
  /^Launching/i,
  /^Creating/i,
  /^\s*$/,  // Empty lines
];

function isUsefulReasoning(content?: string): boolean {
  if (!content) return false;
  const trimmed = content.trim();
  if (trimmed.length < 20) return false;
  return !USELESS_REASONING_PATTERNS.some((pattern) => pattern.test(trimmed));
}

/**
 * Check if content is just status/progress messages (not real AI output).
 * Used to keep thinking expanded until actual content arrives.
 */
function isOnlyStatusMessages(content?: string): boolean {
  if (!content) return true;
  const trimmed = content.trim();
  if (!trimmed) return true;

  // Split into lines and check each
  const lines = trimmed.split('\n').filter(line => line.trim());
  if (lines.length === 0) return true;

  // If every line matches a status pattern, it's only status messages
  return lines.every(line =>
    STATUS_MESSAGE_PATTERNS.some(pattern => pattern.test(line.trim()))
  );
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
  const { text: cleanedTextSansImages, images: inlineImages } = useMemo(
    () => parseImageContent(cleanedText),
    [cleanedText]
  );
  const hasInlineImages = inlineImages.length > 0;
  const hasText = Boolean(cleanedTextSansImages);
  const hasAudio = parsedAudio.length > 0;

  // Strip ANSI codes from reasoning content
  const cleanedReasoning = stripAnsiCodes(message.reasoning_content || '');
  const hasUsefulReasoning = showReasoning && isUsefulReasoning(cleanedReasoning);
  const hasRichContent =
    (Array.isArray(message.content) && message.content.some((part) => part.type !== 'text')) ||
    hasInlineImages;
  const hasArtifacts = Boolean(message.artifacts?.length);
  const imageArtifacts = useMemo(
    () => (message.artifacts || []).filter((artifact) => artifact.type === 'image' && artifact.url),
    [message.artifacts]
  );
  const combinedImageMedia = useMemo<MessageContent | null>(() => {
    if (inlineImages.length === 0 && imageArtifacts.length === 0) return null;
    const seen = new Set<string>();
    const items = [];
    inlineImages.forEach((image) => {
      if (!image.url || seen.has(image.url)) return;
      seen.add(image.url);
      items.push({ type: 'image_url' as const, image_url: { url: image.url } });
    });
    imageArtifacts.forEach((artifact) => {
      if (!artifact.url || seen.has(artifact.url)) return;
      seen.add(artifact.url);
      items.push({ type: 'image_url' as const, image_url: { url: artifact.url } });
    });
    return items.length > 0 ? items : null;
  }, [inlineImages, imageArtifacts]);
  const nonImageArtifacts = useMemo(
    () => (message.artifacts || []).filter((artifact) => artifact.type !== 'image'),
    [message.artifacts]
  );
  const shouldShowPlaceholder =
    !isUser &&
    isStreaming &&
    !hasText &&
    !hasAudio &&
    !hasUsefulReasoning &&
    !hasRichContent &&
    !hasArtifacts;
  const hasRenderableContent =
    hasText ||
    hasAudio ||
    hasUsefulReasoning ||
    hasRichContent ||
    hasArtifacts ||
    shouldShowPlaceholder;
  const displayText = useStreamingBuffer(cleanedTextSansImages, isStreaming && !isUser);
  const canShowActions = hasRenderableContent && !shouldShowPlaceholder;

  // Check if we have real content (not just status messages or empty)
  const hasRealContent = hasText && cleanedText.trim().length > 10 && !isOnlyStatusMessages(cleanedText);

  // Auto-collapse thinking when streaming finishes and real content exists
  // Start expanded (true), then collapse only when done streaming with real content
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);
  const hasAutoCollapsedRef = useRef(false);
  const thinkingContentRef = useRef<HTMLDivElement>(null);

  // Auto-collapse ONCE when streaming is done AND we have real content
  useEffect(() => {
    if (!hasUsefulReasoning) {
      return;
    }
    // Only auto-collapse once, when streaming finishes and we have real content
    // This keeps the thinking section open while the agent is working
    if (!isStreaming && hasRealContent && !hasAutoCollapsedRef.current) {
      hasAutoCollapsedRef.current = true;
      setIsThinkingExpanded(false);
    }
  }, [hasRealContent, hasUsefulReasoning, isStreaming]);

  // Auto-scroll thinking section as new content comes in
  useEffect(() => {
    if (!isThinkingExpanded || !thinkingContentRef.current || !isStreaming) {
      return;
    }

    // Always scroll to bottom when streaming and thinking is expanded
    // Use setTimeout to ensure DOM has updated after content change
    const timeoutId = setTimeout(() => {
      if (thinkingContentRef.current) {
        thinkingContentRef.current.scrollTop = thinkingContentRef.current.scrollHeight;
      }
    }, 50);

    return () => clearTimeout(timeoutId);
  }, [cleanedReasoning, isThinkingExpanded, isStreaming]);

  if (!hasRenderableContent) {
    return null;
  }

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}
      data-testid={isUser ? 'user-message' : 'assistant-message'}
    >
      <div
        className={`chat-message max-w-[94%] sm:max-w-[85%] lg:max-w-[78%] ${
          isUser ? 'chat-message-user' : 'chat-message-assistant'
        }${isStreaming && !isUser ? ' chat-message-streaming' : ''}`}
      >
        {combinedImageMedia ? <MediaRenderer content={combinedImageMedia} /> : null}
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
              <div
                ref={thinkingContentRef}
                className="px-3 pb-3 max-h-48 overflow-y-auto scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent"
              >
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
        {nonImageArtifacts.length > 0 && (
          <div className="mt-2 space-y-1">
            {nonImageArtifacts.map((artifact) => (
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
