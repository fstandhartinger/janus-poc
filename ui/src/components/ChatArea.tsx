'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/store/chat';
import { fetchModels, streamChatCompletion, streamDeepResearch } from '@/lib/api';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { DeepResearchProgress, type ResearchStage } from './DeepResearchProgress';
import { ScreenshotStream } from './ScreenshotStream';
import type { ChatCompletionChunk, MessageContent, Model, ScreenshotData } from '@/types/chat';
import type { AttachedFile } from '@/lib/file-types';

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
    createSession,
    getCurrentSession,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('baseline');
  const [researchStages, setResearchStages] = useState<ResearchStage[]>([]);
  const [researchActive, setResearchActive] = useState(false);
  const [screenshots, setScreenshots] = useState<ScreenshotData[]>([]);
  const [screenshotsLive, setScreenshotsLive] = useState(false);

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

  type MessageContentPart = Exclude<MessageContent, string>[number];
  type SendOptions = { deepResearch?: boolean; researchMode?: 'light' | 'max' };
  type ResearchSource = { title: string; url: string; snippet: string };

  const buildMessageContent = (content: string, files: AttachedFile[]): MessageContent => {
    const trimmedContent = content.trim();
    if (files.length > 0) {
      const parts: MessageContentPart[] = [];
      if (trimmedContent) {
        parts.push({ type: 'text', text: trimmedContent });
      }
      files.forEach((file) => {
        if (file.category === 'images') {
          parts.push({ type: 'image_url', image_url: { url: file.content } });
        } else {
          parts.push({
            type: 'file',
            file: {
              name: file.name,
              mime_type: file.type || 'application/octet-stream',
              content: file.content,
              size: file.size,
            },
          });
        }
      });
      return parts;
    }
    return trimmedContent;
  };

  const normalizeStageStatus = (status?: string): ResearchStage['status'] => {
    if (status === 'pending' || status === 'running' || status === 'complete' || status === 'error') {
      return status;
    }
    return 'pending';
  };

  const updateResearchStage = (payload: { label?: string; status?: string; detail?: string }) => {
    const label = payload.label?.trim();
    if (!label) return;
    const status = normalizeStageStatus(payload.status);
    const detail = payload.detail?.trim();
    setResearchStages((prev) => {
      const next = [...prev];
      const existingIndex = next.findIndex((stage) => stage.label === label);
      if (existingIndex >= 0) {
        next[existingIndex] = {
          ...next[existingIndex],
          status,
          detail,
        };
      } else {
        next.push({
          id: label,
          label,
          status,
          detail,
        });
      }
      return next;
    });
  };

  const collectResearchSources = (
    raw: unknown,
    sources: ResearchSource[],
    seen: Set<string>
  ) => {
    const entries: Array<Record<string, unknown>> = [];
    if (Array.isArray(raw)) {
      for (const entry of raw) {
        if (Array.isArray(entry)) {
          entries.push(...(entry.filter((item) => item && typeof item === 'object') as Record<string, unknown>[]));
        } else if (entry && typeof entry === 'object') {
          entries.push(entry as Record<string, unknown>);
        }
      }
    } else if (raw && typeof raw === 'object') {
      entries.push(raw as Record<string, unknown>);
    }

    for (const entry of entries) {
      const metadata =
        entry.metadata && typeof entry.metadata === 'object'
          ? (entry.metadata as Record<string, unknown>)
          : {};
      const title = String(metadata.title ?? entry.title ?? '');
      const url = String(metadata.url ?? entry.url ?? '');
      const snippet = String(entry.pageContent ?? entry.snippet ?? '');
      const key = url || title;
      if (key && seen.has(key)) continue;
      if (key) seen.add(key);
      sources.push({ title, url, snippet: snippet.slice(0, 200) });
    }
  };

  const appendResearchSources = (sources: ResearchSource[]) => {
    const lines = sources.map((source, index) => {
      const title = source.title || source.url || `Source ${index + 1}`;
      if (source.url) {
        return `${index + 1}. [${title}](${source.url})`;
      }
      return `${index + 1}. ${title}`;
    });
    appendToLastMessage(`\n\n---\n\n## Sources\n\n${lines.join('\n')}`, '');
  };

  const pushScreenshot = (shot: ScreenshotData) => {
    if (!shot.image_base64) return;
    setScreenshots((prev) => [...prev, shot]);
  };

  const coerceScreenshotPayload = (payload: unknown): ScreenshotData | null => {
    if (!payload || typeof payload !== 'object') return null;
    const data = payload as Record<string, unknown>;
    const image = typeof data.image_base64 === 'string' ? data.image_base64 : '';
    if (!image) return null;
    return {
      url: typeof data.url === 'string' ? data.url : '',
      title: typeof data.title === 'string' ? data.title : '',
      image_base64: image,
      timestamp: typeof data.timestamp === 'number' ? data.timestamp : Date.now() / 1000,
    };
  };

  const handleSend = async (content: string, files: AttachedFile[], options?: SendOptions) => {
    // Ensure we have a session
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createSession();
    }

    // Build message content
    const messageContent = buildMessageContent(content, files);
    const trimmedContent = content.trim();

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
    setScreenshots([]);
    setScreenshotsLive(true);
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    const useDeepResearch = Boolean(options?.deepResearch && trimmedContent);
    const sources: ResearchSource[] = [];
    const seenSources = new Set<string>();
    let aborted = false;

    if (useDeepResearch) {
      setResearchStages([]);
      setResearchActive(true);
    }

    try {
      if (useDeepResearch) {
        for await (const event of streamDeepResearch(
          {
            query: trimmedContent,
            mode: options?.researchMode ?? 'light',
            optimization: 'balanced',
          },
          signal
        )) {
          if (event.type === 'progress') {
            updateResearchStage({
              label: event.data?.label,
              status: event.data?.status,
              detail: event.data?.detail,
            });
          } else if (event.type === 'response') {
            appendToLastMessage(event.data || '', '');
          } else if (event.type === 'sources') {
            collectResearchSources(event.data, sources, seenSources);
          } else if (event.type === 'error') {
            const detail = event.data?.detail;
            if (detail) {
              appendToLastMessage(`\n\n*${detail}*`, '');
            }
          }
        }
      } else {
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
          signal
        )) {
          if ('type' in chunk && chunk.type === 'screenshot') {
            pushScreenshot(chunk.data);
            continue;
          }
          const completionChunk = chunk as ChatCompletionChunk;
          const delta = completionChunk.choices[0]?.delta;
          if (delta?.janus?.event === 'screenshot') {
            const payload = coerceScreenshotPayload(delta.janus.payload);
            if (payload) {
              pushScreenshot(payload);
            }
            continue;
          }
          if (delta) {
            const contentDelta = delta.content || '';
            const reasoningDelta = delta.reasoning_content || '';
            if (contentDelta || reasoningDelta) {
              appendToLastMessage(contentDelta, reasoningDelta);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // User cancelled
        aborted = true;
      } else {
        console.error('Streaming error:', error);
        appendToLastMessage('\n\n*Error: Failed to get response*', '');
      }
    } finally {
      if (useDeepResearch && !aborted && sources.length > 0) {
        appendResearchSources(sources);
      }
      if (useDeepResearch) {
        setResearchActive(false);
      }
      setScreenshotsLive(false);
      setStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancel = () => {
    abortControllerRef.current?.abort();
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="chat-topbar shrink-0">
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
          <Link href="/" className="chat-home-btn" title="Go to home" aria-label="Go to home">
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
          </Link>
          <span className="chat-context">Session</span>
          <span className="chat-session-title">{session?.title || 'New chat'}</span>
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
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 px-6 py-6">
        <div className="max-w-4xl mx-auto">
          <DeepResearchProgress stages={researchStages} isActive={researchActive} />
          <ScreenshotStream screenshots={screenshots} isLive={screenshotsLive} />
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
              <span>{researchActive ? 'Running deep research' : 'Generating response'}</span>
              <button onClick={handleCancel} className="chat-cancel">
                Stop
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 px-6 pb-6 pt-2">
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
