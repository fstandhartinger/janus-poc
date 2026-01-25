'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/store/chat';
import { useCanvasStore } from '@/store/canvas';
import { RateLimitError, fetchModels, streamChatCompletion, streamDeepResearch } from '@/lib/api';
import { isMemoryEnabled } from '@/lib/memory';
import { FREE_CHAT_LIMIT, incrementFreeChatCount, readFreeChatState, remainingFreeChats, setFreeChatCount } from '@/lib/freeChat';
import { getUserId } from '@/lib/userId';
import { handleCanvasContent, parseCanvasBlocks } from '@/lib/canvas-parser';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { DeepResearchProgress, type ResearchStage } from './DeepResearchProgress';
import { ScreenshotStream } from './ScreenshotStream';
import { CanvasPanel } from './canvas';
import { ModelSelector } from './ModelSelector';
import { MemoryToggle } from './MemoryToggle';
import { SignInGateDialog } from './auth/SignInGateDialog';
import { UserMenu } from './auth/UserMenu';
import { useAuth } from '@/hooks/useAuth';
import type { ChatCompletionChunk, MessageContent, Model, ScreenshotData } from '@/types/chat';
import type { AttachedFile } from '@/lib/file-types';

interface ChatAreaProps {
  onMenuClick?: () => void;
  isSidebarCollapsed?: boolean;
  onNewChat?: () => void;
}

export function ChatArea({ onMenuClick, isSidebarCollapsed, onNewChat }: ChatAreaProps) {
  const {
    currentSessionId,
    isStreaming,
    showReasoning,
    addMessage,
    appendToLastMessage,
    updateLastMessage,
    setStreaming,
    createSession,
    getCurrentSession,
  } = useChatStore();

  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated, isLoading: authLoading, signIn, signOut } = useAuth();
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const processedCanvasMessagesRef = useRef<Set<string>>(new Set());
  const pendingSendRef = useRef<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('baseline-cli-agent');
  const [researchStages, setResearchStages] = useState<ResearchStage[]>([]);
  const [researchActive, setResearchActive] = useState(false);
  const [screenshots, setScreenshots] = useState<ScreenshotData[]>([]);
  const [screenshotsLive, setScreenshotsLive] = useState(false);
  const [freeChatsRemaining, setFreeChatsRemaining] = useState(FREE_CHAT_LIMIT);
  const [freeChatsUsed, setFreeChatsUsed] = useState(0);
  const [signInGateOpen, setSignInGateOpen] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | undefined>();
  const [toast, setToast] = useState<{ message: string; action?: string; onAction?: () => void } | null>(null);

  const session = getCurrentSession();
  const messages = session?.messages || [];
  const pendingQuery = searchParams.get('q')?.trim();

  const syncFreeChatState = () => {
    const state = readFreeChatState();
    setFreeChatsUsed(state.count);
    setFreeChatsRemaining(Math.max(0, FREE_CHAT_LIMIT - state.count));
  };

  useEffect(() => {
    getUserId(user);
  }, [user]);

  useEffect(() => {
    syncFreeChatState();
  }, []);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === 'janus_free_chats_v1') {
        syncFreeChatState();
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  // Auto-scroll to bottom - use scrollTop on container to avoid propagating to parent
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    let isMounted = true;
    const fallbackModels: Model[] = [
      { id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' },
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
    const trimmedContent = content.trim();

    if (!authLoading && !isAuthenticated && remainingFreeChats() <= 0) {
      setPendingMessage(trimmedContent || undefined);
      setSignInGateOpen(true);
      setToast({
        message: 'Daily limit reached. Sign in to continue.',
        action: 'Sign in',
        onAction: () => signIn(trimmedContent || undefined),
      });
      return;
    }

    // Ensure we have a session
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createSession();
    }

    if (!isAuthenticated) {
      const state = incrementFreeChatCount();
      setFreeChatsUsed(state.count);
      setFreeChatsRemaining(Math.max(0, FREE_CHAT_LIMIT - state.count));
    }

    // Build message content
    const messageContent = buildMessageContent(content, files);

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

        const userId = getUserId(user);
        const memoryEnabled = isMemoryEnabled();

        for await (const chunk of streamChatCompletion(
          {
            model: selectedModel,
            messages: requestMessages,
            stream: true,
            user_id: userId,
            enable_memory: memoryEnabled,
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
      } else if (error instanceof RateLimitError) {
        const message = error.message || 'Daily limit reached. Sign in to continue.';
        console.error('Rate limit error:', error);
        updateLastMessage({
          content: message,
          reasoning_content: '',
        });
        setPendingMessage(trimmedContent || undefined);
        setSignInGateOpen(true);
        setToast({
          message,
          action: 'Sign in',
          onAction: () => signIn(trimmedContent || undefined),
        });
        setFreeChatCount(FREE_CHAT_LIMIT);
        setFreeChatsUsed(FREE_CHAT_LIMIT);
        setFreeChatsRemaining(0);
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

  useEffect(() => {
    if (!pendingQuery || !isAuthenticated || isStreaming) return;
    if (pendingSendRef.current === pendingQuery) return;
    pendingSendRef.current = pendingQuery;
    handleSend(pendingQuery, []);
    setPendingMessage(undefined);
    setSignInGateOpen(false);
    const url = new URL(window.location.href);
    url.searchParams.delete('q');
    router.replace(`${url.pathname}${url.search}`);
  }, [handleSend, isAuthenticated, isStreaming, pendingQuery, router]);

  const getMessageText = (content: MessageContent) => {
    if (typeof content === 'string') {
      return content;
    }
    return (content || [])
      .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
      .map((part) => part.text)
      .join('\n');
  };

  useEffect(() => {
    if (isStreaming) return;
    const lastAssistantMessage = [...messages].reverse().find((message) => message.role === 'assistant');
    if (!lastAssistantMessage) return;
    if (processedCanvasMessagesRef.current.has(lastAssistantMessage.id)) return;

    const textContent = getMessageText(lastAssistantMessage.content);
    if (!textContent) return;

    const blocks = parseCanvasBlocks(textContent);
    if (blocks.length === 0) return;

    handleCanvasContent(textContent);
    processedCanvasMessagesRef.current.add(lastAssistantMessage.id);
  }, [isStreaming, messages]);

  const handleAIEdit = (instruction: string) => {
    if (isStreaming) return;
    const doc = useCanvasStore.getState().getActiveDocument();
    if (!doc) return;
    const message = `Please edit the canvas content (${doc.title}):\n\nInstruction: ${instruction}\n\nCurrent content:\n\n\`\`\`${doc.language}\n${doc.content}\n\`\`\``;
    handleSend(message, []);
  };

  return (
    <div className="chat-area">
      <CanvasPanel onAIEdit={handleAIEdit} disabled={isStreaming} />
      <div className="chat-topbar shrink-0">
        <div className="chat-topbar-left">
          {/* Menu button - visible on mobile OR on desktop when sidebar is collapsed */}
          <button
            type="button"
            onClick={onMenuClick}
            className={`chat-menu-btn ${isSidebarCollapsed ? 'lg:flex' : 'lg:hidden'}`}
            aria-label="Open sidebar"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          {/* New chat button - visible on desktop when sidebar is collapsed */}
          {isSidebarCollapsed && onNewChat && (
            <button
              type="button"
              onClick={onNewChat}
              className="chat-new-chat-btn hidden lg:flex"
              aria-label="New chat"
              title="New chat"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
            </button>
          )}
          <Link href="/" className="chat-home-btn" title="Go to home" aria-label="Go to home">
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
          </Link>
          <span className="chat-context">Session</span>
          <span className="chat-session-title">{session?.title || 'New chat'}</span>
        </div>

        <div className="chat-topbar-right">
          <div className="chat-auth">
            {!authLoading && !isAuthenticated && (
              <>
                <button type="button" className="chat-signin-btn" onClick={() => signIn()}>
                  Sign in
                </button>
                <div className="chat-free-count">
                  {freeChatsRemaining}/{FREE_CHAT_LIMIT} free chats remaining
                </div>
              </>
            )}
            {isAuthenticated && user && (
              <UserMenu userId={user.userId} username={user.username} onSignOut={signOut} />
            )}
          </div>
          <MemoryToggle />
          <ModelSelector
            models={models.length ? models : [{ id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' }]}
            selectedModel={selectedModel}
            onSelect={setSelectedModel}
          />
        </div>
      </div>

      <SignInGateDialog
        open={signInGateOpen}
        onOpenChange={setSignInGateOpen}
        usedCount={freeChatsUsed}
        limit={FREE_CHAT_LIMIT}
        pendingMessage={pendingMessage}
      />

      {toast && (
        <div className="chat-toast" role="status" aria-live="polite">
          <div className="toast toast-error">
            <span>{toast.message}</span>
            {toast.action && toast.onAction && (
              <button
                type="button"
                onClick={() => {
                  toast.onAction?.();
                  setToast(null);
                }}
                className="chat-toast-action"
              >
                {toast.action}
              </button>
            )}
          </div>
        </div>
      )}

      {messages.length === 0 ? (
        /* Empty state: center everything vertically */
        <div className="chat-empty-container flex-1 flex flex-col items-center justify-center px-6 py-6">
          <div className="w-full max-w-2xl">
            <div className="text-center mb-8">
              <p className="chat-empty-title">Where should we begin?</p>
              <p className="chat-empty-subtitle">
                Powered by Chutes. The world&apos;s open-source decentralized AI compute platform.
              </p>
            </div>
            <ChatInput onSend={handleSend} disabled={isStreaming} />
          </div>
        </div>
      ) : (
        /* Chat mode: messages scroll, input fixed at bottom */
        <>
          <div ref={messagesContainerRef} className="chat-messages-container px-6 py-6" aria-busy={isStreaming}>
            <div className="max-w-4xl mx-auto">
              <DeepResearchProgress stages={researchStages} isActive={researchActive} />
              <ScreenshotStream screenshots={screenshots} isLive={screenshotsLive} />
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  showReasoning={showReasoning}
                />
              ))}

              {isStreaming && (
                <div className="chat-streaming" role="status" aria-live="polite">
                  <span className="chat-streaming-dot" />
                  <span>{researchActive ? 'Running deep research' : 'Generating response'}</span>
                  <button onClick={handleCancel} className="chat-cancel">
                    Stop
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="chat-input-bottom px-6">
            <div className="max-w-4xl mx-auto">
              <ChatInput onSend={handleSend} disabled={isStreaming} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
