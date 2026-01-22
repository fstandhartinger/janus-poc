'use client';

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/store/chat';
import { streamChatCompletion } from '@/lib/api';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import type { MessageContent } from '@/types/chat';

export function ChatArea() {
  const {
    currentSessionId,
    isStreaming,
    showReasoning,
    addMessage,
    appendToLastMessage,
    setStreaming,
    toggleReasoning,
    createSession,
    getCurrentSession,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const session = getCurrentSession();
  const messages = session?.messages || [];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content: string, images: string[]) => {
    // Ensure we have a session
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createSession();
    }

    // Build message content
    let messageContent: MessageContent;
    if (images.length > 0) {
      const parts: MessageContent = [];
      if (content) {
        parts.push({ type: 'text', text: content });
      }
      images.forEach((url) => {
        parts.push({ type: 'image_url', image_url: { url } });
      });
      messageContent = parts;
    } else {
      messageContent = content;
    }

    // Add user message
    addMessage({
      role: 'user',
      content: messageContent,
    });

    // Add placeholder for assistant response
    addMessage({
      role: 'assistant',
      content: '',
      reasoning_content: '',
    });

    // Start streaming
    setStreaming(true);
    abortControllerRef.current = new AbortController();

    try {
      // Build request messages from current session
      const currentSession = getCurrentSession();
      const requestMessages = (currentSession?.messages || [])
        .slice(0, -1) // Exclude the placeholder
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      for await (const chunk of streamChatCompletion(
        {
          model: 'baseline',
          messages: requestMessages,
          stream: true,
        },
        abortControllerRef.current.signal
      )) {
        const delta = chunk.choices[0]?.delta;
        if (delta) {
          const contentDelta = delta.content || '';
          const reasoningDelta = delta.reasoning_content || '';
          if (contentDelta || reasoningDelta) {
            appendToLastMessage(contentDelta, reasoningDelta);
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // User cancelled
      } else {
        console.error('Streaming error:', error);
        appendToLastMessage('\n\n*Error: Failed to get response*', '');
      }
    } finally {
      setStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancel = () => {
    abortControllerRef.current?.abort();
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b dark:border-gray-700">
        <h2 className="font-medium text-gray-700 dark:text-gray-200">
          {session?.title || 'Select or create a chat'}
        </h2>
        <button
          onClick={toggleReasoning}
          className={`px-3 py-1 text-sm rounded ${
            showReasoning
              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
          }`}
        >
          {showReasoning ? '💭 Thinking: ON' : '💭 Thinking: OFF'}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <div className="text-4xl mb-2">👋</div>
              <p>Start a conversation</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                showReasoning={showReasoning}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <div className="animate-pulse">●</div>
            <span>Generating...</span>
            <button
              onClick={handleCancel}
              className="text-red-500 hover:text-red-600"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
