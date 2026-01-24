'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { FileContent, Message } from '@/types/chat';
import { FileIcon } from './FileIcon';
import { detectFileCategoryFromMetadata, formatBytes } from '@/lib/file-utils';

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
}

export function MessageBubble({ message, showReasoning }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const contentParts = typeof message.content === 'string' ? [] : message.content || [];
  const content =
    typeof message.content === 'string'
      ? message.content
      : contentParts
          .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
          .map((c) => c.text)
          .join('\n');

  const imageParts =
    typeof message.content === 'string'
      ? []
      : message.content.filter(
          (c): c is { type: 'image_url'; image_url: { url: string } } => c.type === 'image_url'
        );

  const fileParts =
    typeof message.content === 'string'
      ? []
      : message.content.filter((c): c is FileContent => c.type === 'file');

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
        {fileParts.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {fileParts.map((part, i) => {
              const file = part.file;
              const category = detectFileCategoryFromMetadata(file.name, file.mime_type) || 'text';
              return (
                <div
                  key={`${file.name}-${i}`}
                  className="flex items-center gap-2 rounded-lg border border-[#1F2937] bg-[#0F172A]/70 p-2 max-w-[240px]"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded bg-[#1F2937] text-[#9CA3AF]">
                    <FileIcon category={category} className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-[#E5E7EB]">{file.name}</p>
                    <p className="text-xs text-[#6B7280]">{formatBytes(file.size)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Show attached images */}
        {imageParts.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {imageParts.map((part, i) => (
              <img
                key={i}
                src={part.image_url.url}
                alt="Attached"
                className="max-w-[200px] max-h-[200px] rounded-lg border border-[#1F2937]"
              />
            ))}
          </div>
        )}

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
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>

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
