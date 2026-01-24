'use client';
import type { Message } from '@/types/chat';
import { stripCanvasBlocks } from '@/lib/canvas-parser';
import { AudioPlayer } from './AudioPlayer';
import { MediaRenderer } from './MediaRenderer';
import { TTSPlayer } from './TTSPlayer';
import { RichContent } from './viz/RichContent';

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
}

const AUDIO_DATA_REGEX = /data:audio\/(wav|mp3|ogg);base64,[A-Za-z0-9+/=]+/g;

function extractAudioContent(content: string) {
  if (!content) {
    return { cleanedText: content, audioUrls: [] as string[] };
  }

  const audioUrls = content.match(AUDIO_DATA_REGEX) ?? [];
  if (audioUrls.length === 0) {
    return { cleanedText: content, audioUrls };
  }

  const cleanedText = content
    .replace(AUDIO_DATA_REGEX, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return { cleanedText, audioUrls };
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
  const { cleanedText, audioUrls } = extractAudioContent(textContent);
  const hasText = Boolean(cleanedText);

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

        {/* Show reasoning panel if available */}
        {showReasoning && message.reasoning_content && (
          <div className="mb-3 p-3 rounded-lg text-sm border border-[#1F2937] bg-[#111726]/70">
            <div className="text-[11px] uppercase tracking-[0.2em] text-[#F59E0B] font-semibold mb-2">
              Thinking
            </div>
            <div className="text-[#D1D5DB] whitespace-pre-wrap">
              {message.reasoning_content}
            </div>
          </div>
        )}

        {/* Message content */}
        {hasText && (
          <RichContent content={cleanedText} />
        )}

        {audioUrls.length > 0 && (
          <div className="mt-3 space-y-2">
            {audioUrls.map((url, index) => (
              <AudioPlayer
                key={`${message.id}-audio-${index}`}
                src={url}
                title={`Generated Audio ${index + 1}`}
                downloadName={`audio-${index + 1}.wav`}
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
