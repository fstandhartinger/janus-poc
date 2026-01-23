'use client';

import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/store/chat';
import { fetchModels, streamChatCompletion } from '@/lib/api';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import type { MessageContent, Model } from '@/types/chat';

interface ChatAreaProps {
  onMenuClick?: () => void;
}

export function ChatArea({ onMenuClick }: ChatAreaProps) {
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
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('baseline');

  const session = getCurrentSession();
  const messages = session?.messages || [];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    let isMounted = true;
    const fallbackModels: Model[] = [
      { id: 'baseline', object: 'model', created: 0, owned_by: 'janus' },
    ];

    fetchModels()
      .then((data) => {
        if (!isMounted) return;
        const available = data.length ? data : fallbackModels;
        setModels(available);
        setSelectedModel((current) =>
          available.some((model) => model.id === current) ? current : available[0].id
        );
      })
      .catch(() => {
        if (!isMounted) return;
        setModels(fallbackModels);
      });

    return () => {
      isMounted = false;
    };
  }, []);

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
          model: selectedModel,
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
      <div className="chat-topbar">
        <div className="chat-topbar-left">
          <button
            type="button"
            onClick={onMenuClick}
            className="chat-menu-btn lg:hidden"
            aria-label="Open sidebar"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="chat-context">Session</span>
          <span className="chat-session-title">{session?.title || 'Where should we begin?'}</span>
        </div>

        <div className="chat-topbar-right">
          <div className="chat-model-select">
            <span className="chat-model-label">Model</span>
            <select
              value={selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
              className="chat-model-dropdown"
              data-testid="model-select"
            >
              {(models.length
                ? models
                : [{ id: 'baseline', object: 'model', created: 0, owned_by: 'janus' }]
              ).map((model) => (
                <option key={model.id} value={model.id}>
                  {model.id}
                </option>
              ))}
            </select>
          </div>
          <button onClick={toggleReasoning} className="chat-toggle">
            {showReasoning ? 'Thinking: On' : 'Thinking: Off'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <div>
                <p className="chat-empty-title">Where should we begin?</p>
                <p className="chat-empty-subtitle">
                  Powered by Chutes. The world's open-source decentralized AI compute platform.
                </p>
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

          {isStreaming && (
            <div className="chat-streaming">
              <span className="chat-streaming-dot" />
              <span>Generating response</span>
              <button onClick={handleCancel} className="chat-cancel">
                Stop
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="px-6 pb-6">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
