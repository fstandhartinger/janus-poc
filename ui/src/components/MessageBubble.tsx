'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types/chat';

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
}

export function MessageBubble({ message, showReasoning }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const content =
    typeof message.content === 'string'
      ? message.content
      : message.content
          .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
          .map((c) => c.text)
          .join('\n');

  const hasImages =
    typeof message.content !== 'string' &&
    message.content.some((c) => c.type === 'image_url');

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
        }`}
      >
        {/* Show attached images */}
        {hasImages && typeof message.content !== 'string' && (
          <div className="mb-2 flex flex-wrap gap-2">
            {message.content
              .filter((c): c is { type: 'image_url'; image_url: { url: string } } => c.type === 'image_url')
              .map((c, i) => (
                <img
                  key={i}
                  src={c.image_url.url}
                  alt="Attached"
                  className="max-w-[200px] max-h-[200px] rounded"
                />
              ))}
          </div>
        )}

        {/* Show reasoning panel if available */}
        {showReasoning && message.reasoning_content && (
          <div className="mb-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded text-sm border-l-2 border-yellow-400">
            <div className="text-xs text-yellow-600 dark:text-yellow-400 font-medium mb-1">
              Thinking...
            </div>
            <div className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
              {message.reasoning_content}
            </div>
          </div>
        )}

        {/* Message content */}
        <div className="prose dark:prose-invert prose-sm max-w-none">
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
                className="flex items-center gap-2 p-2 bg-white/10 rounded text-sm hover:bg-white/20 transition-colors"
              >
                <span className="text-blue-400">📎</span>
                <span className="truncate">{artifact.display_name}</span>
                <span className="text-xs text-gray-400">
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
