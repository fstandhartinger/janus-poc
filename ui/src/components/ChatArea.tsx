'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useChatStore } from '@/store/chat';
import { useCanvasStore } from '@/store/canvas';
import { useSettingsStore } from '@/store/settings';
import {
  RateLimitError,
  RequestTimeoutError,
  fetchModels,
  streamChatCompletion,
  streamDeepResearch,
  type DeepResearchProgressPayload,
} from '@/lib/api';
import { isMemoryEnabled, setMemoryEnabled } from '@/lib/memory';
import { FREE_CHAT_LIMIT, incrementFreeChatCount, readFreeChatState, remainingFreeChats, setFreeChatCount } from '@/lib/freeChat';
import { getUserId } from '@/lib/userId';
import { handleCanvasContent, parseCanvasBlocks } from '@/lib/canvas-parser';
import { useDebug } from '@/hooks/useDebug';
import { useSmartScroll } from '@/hooks/useSmartScroll';
import { cacheArtifact } from '@/lib/artifact-client';
import logger from '@/lib/logger';
import { useArena } from '@/hooks/useArena';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { DeepResearchProgress, type ResearchStage } from './DeepResearchProgress';
import { ScreenshotStream } from './ScreenshotStream';
import { CanvasPanel } from './canvas';
import { ModelSelector } from './ModelSelector';
import { AgentSelector, type AgentOption } from './AgentSelector';
import { AgentStatusIndicator } from './chat/AgentStatusIndicator';
import { EmptyState } from './chat/EmptyState';
import { QuickSuggestions } from './chat/QuickSuggestions';
import { DebugPanel } from './debug/DebugPanel';
import { DebugToggle } from './debug/DebugToggle';
import { MemoryToggle } from './MemoryToggle';
import { ChatOverflowMenu } from './ChatOverflowMenu';
import { MemorySheet } from './memory/MemorySheet';
import { SessionSheet } from './sessions/SessionSheet';
import { SignInGateDialog } from './auth/SignInGateDialog';
import { UserMenu } from './auth/UserMenu';
import { ShareModal } from './ShareModal';
import { ArenaToggle } from './arena/ArenaToggle';
import { useAuth } from '@/hooks/useAuth';
import type { Artifact, ChatCompletionChunk, MessageContent, Model, ScreenshotData } from '@/types/chat';
import type { GenerationFlags } from '@/types/generation';
import type { AttachedFile } from '@/lib/file-types';

interface ChatAreaProps {
  onMenuClick?: () => void;
  onNewChat?: () => void;
  initialMessage?: string;
  autoSubmit?: boolean;
}

type ResearchSource = {
  title: string;
  url: string;
  snippet: string;
};

const AGENT_OPTIONS: AgentOption[] = [
  { id: 'claude-code', label: 'Claude Code', badges: ['Shell', 'Web', 'Downloads', 'Code'] },
  { id: 'roo-code', label: 'Roo Code', badges: ['TBD'] },
  { id: 'cline', label: 'Cline', badges: ['TBD'] },
  { id: 'opencode', label: 'OpenCode', badges: ['TBD'] },
  { id: 'codex', label: 'Codex', badges: ['TBD'] },
  { id: 'aider', label: 'Aider', badges: ['Code'] },
];

const getMessageText = (content: MessageContent) => {
  if (typeof content === 'string') {
    return content;
  }
  return (content || [])
    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
    .map((part) => part.text)
    .join('\n');
};

export function ChatArea({
  onMenuClick,
  onNewChat,
  initialMessage,
  autoSubmit,
}: ChatAreaProps) {
  const {
    currentSessionId,
    isStreaming,
    showReasoning,
    addMessage,
    appendToLastMessage,
    appendArtifacts,
    updateLastMessage,
    setStreaming,
    createSession,
    getCurrentSession,
  } = useChatStore();

  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated, isLoading: authLoading, signIn, signOut } = useAuth();
  const { arenaMode, requestArenaCompletion } = useArena();
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const processedCanvasMessagesRef = useRef<Set<string>>(new Set());
  const pendingSendRef = useRef<string | null>(null);
  const shareHandledRef = useRef<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState('baseline-cli-agent');
  const [selectedAgent, setSelectedAgent] = useState('claude-code');
  const [screenshots, setScreenshots] = useState<ScreenshotData[]>([]);
  const [screenshotsLive, setScreenshotsLive] = useState(false);
  const [freeChatsRemaining, setFreeChatsRemaining] = useState(FREE_CHAT_LIMIT);
  const [freeChatsUsed, setFreeChatsUsed] = useState(0);
  const [signInGateOpen, setSignInGateOpen] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | undefined>();
  const [toast, setToast] = useState<{ message: string; action?: string; onAction?: () => void } | null>(null);
  const [memorySheetOpen, setMemorySheetOpen] = useState(false);
  const [sessionSheetOpen, setSessionSheetOpen] = useState(false);
  const [memoryEnabled, setMemoryEnabledState] = useState(() => isMemoryEnabled());
  const [prefillMessage, setPrefillMessage] = useState<string | undefined>();
  const [shareOpen, setShareOpen] = useState(false);
  const [deepResearchStages, setDeepResearchStages] = useState<ResearchStage[]>([]);
  const [deepResearchActive, setDeepResearchActive] = useState(false);
  const deepResearchSourcesRef = useRef<ResearchSource[]>([]);
  const deepResearchSeenRef = useRef<Set<string>>(new Set());
  const ttsAutoPlay = useSettingsStore((state) => state.ttsAutoPlay);
  const setTTSAutoPlay = useSettingsStore((state) => state.setTTSAutoPlay);
  const debugMode = useSettingsStore((state) => state.debugMode);
  const setDebugMode = useSettingsStore((state) => state.setDebugMode);

  const session = getCurrentSession();
  const messages = session?.messages || [];
  const lastDebugRequestId = useMemo(() => {
    const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant');
    return lastAssistant?.metadata?.requestId || null;
  }, [messages]);
  const lastMessageContent = messages.length
    ? getMessageText(messages[messages.length - 1].content)
    : '';
  const { resetUserScroll } = useSmartScroll(messagesContainerRef, [lastMessageContent, isStreaming]);
  const debugState = useDebug(debugMode, lastDebugRequestId, selectedModel);
  const isCliAgentModel = selectedModel.includes('cli-agent');

  const updateLastMessageMetadata = useCallback(
    (updates: Partial<NonNullable<(typeof messages)[number]['metadata']>>) => {
      const current = getCurrentSession();
      const lastMessage = current?.messages[current.messages.length - 1];
      const existing = lastMessage?.metadata ?? {};
      updateLastMessage({ metadata: { ...existing, ...updates } });
    },
    [getCurrentSession, updateLastMessage]
  );
  const lastAssistantIndex = messages.reduce(
    (lastIndex, message, index) => (message.role === 'assistant' ? index : lastIndex),
    -1
  );
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

  const handleAutoPlayHandled = useCallback(() => {
    setTTSAutoPlay(false);
  }, [setTTSAutoPlay]);
  const openShare = useCallback(() => setShareOpen(true), []);
  const closeShare = useCallback(() => setShareOpen(false), []);
  useEffect(() => {
    if (isStreaming) {
      resetUserScroll();
    }
  }, [isStreaming, resetUserScroll]);

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

  const coerceArtifact = (payload: unknown): Artifact | null => {
    if (!payload || typeof payload !== 'object') return null;
    const candidate = payload as Partial<Artifact>;
    if (!candidate.id || !candidate.url || !candidate.display_name) {
      return null;
    }
    return candidate as Artifact;
  };

  const coerceArtifactsPayload = (payload: unknown): Artifact[] => {
    if (!payload) return [];
    if (Array.isArray(payload)) {
      return payload.map(coerceArtifact).filter(Boolean) as Artifact[];
    }
    if (typeof payload !== 'object') return [];
    const candidate = payload as { items?: unknown };
    const items = Array.isArray(candidate.items) ? candidate.items : [];
    return items.map(coerceArtifact).filter(Boolean) as Artifact[];
  };

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

  const normalizeResearchStatus = (
    status?: DeepResearchProgressPayload['status']
  ): ResearchStage['status'] => {
    if (status === 'pending' || status === 'running' || status === 'complete' || status === 'error') {
      return status;
    }
    return 'running';
  };

  const upsertResearchStage = (payload: DeepResearchProgressPayload) => {
    const label = payload.label?.trim();
    if (!label) return;
    const status = normalizeResearchStatus(payload.status);
    const detail = payload.detail?.trim();
    setDeepResearchStages((prev) => {
      const next = [...prev];
      const index = next.findIndex((item) => item.label === label);
      const stage: ResearchStage = {
        id: label,
        label,
        status,
        detail: detail || undefined,
      };
      if (index >= 0) {
        next[index] = { ...next[index], ...stage };
      } else {
        next.push(stage);
      }
      return next;
    });
  };

  const collectResearchSources = (raw: unknown) => {
    const queue = Array.isArray(raw) ? [...raw] : [raw];
    const sources = deepResearchSourcesRef.current;
    const seen = deepResearchSeenRef.current;

    const addSource = (entry: Record<string, unknown>) => {
      const metadata = entry.metadata;
      const meta =
        metadata && typeof metadata === 'object' ? (metadata as Record<string, unknown>) : {};
      const title = String(meta.title || entry.title || entry.name || '').trim();
      const url = String(meta.url || entry.url || entry.link || '').trim();
      const snippet = String(entry.pageContent || entry.snippet || entry.description || '').trim();
      const key = url || title;
      if (key && seen.has(key)) return;
      if (key) {
        seen.add(key);
      }
      sources.push({ title, url, snippet });
    };

    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) continue;
      if (Array.isArray(item)) {
        queue.push(...item);
        continue;
      }
      if (typeof item === 'object') {
        addSource(item as Record<string, unknown>);
      }
    }
  };

  const formatResearchSources = (sources: ResearchSource[]) => {
    if (!sources.length) return '';
    const lines = ['\n\n---\n\n## Sources\n'];
    sources.forEach((source, index) => {
      const label = source.title || source.url || `Source ${index + 1}`;
      if (source.url) {
        lines.push(`${index + 1}. [${label}](${source.url})`);
      } else {
        lines.push(`${index + 1}. ${label}`);
      }
    });
    return lines.join('\n');
  };

  const streamResearch = async (
    query: string,
    mode: 'light' | 'max',
    signal: AbortSignal
  ) => {
    setDeepResearchActive(true);
    setDeepResearchStages([]);
    deepResearchSourcesRef.current = [];
    deepResearchSeenRef.current = new Set();

    try {
      for await (const event of streamDeepResearch(
        { query, mode, optimization: 'balanced' },
        signal
      )) {
        if (event.type === 'progress') {
          upsertResearchStage(event.data as DeepResearchProgressPayload);
          continue;
        }
        if (event.type === 'sources') {
          collectResearchSources(event.data);
          continue;
        }
        if (event.type === 'response') {
          appendToLastMessage(event.data || '', '');
          continue;
        }
        if (event.type === 'error') {
          const detail = event.data?.detail || 'Deep research failed.';
          appendToLastMessage(`\n\n*${detail}*`, '');
        }
      }
    } finally {
      const sources = deepResearchSourcesRef.current;
      if (sources.length) {
        appendToLastMessage(formatResearchSources(sources), '');
      }
      setDeepResearchActive(false);
    }
  };

  const handleSend = async (
    content: string,
    files: AttachedFile[],
    generationFlags?: GenerationFlags
  ) => {
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
      arena: arenaMode
        ? {
            promptId: '',
            responseA: { content: '' },
            responseB: { content: '' },
          }
        : undefined,
    });

    // Start streaming
    resetUserScroll();
    setStreaming(true);
    setScreenshots([]);
    const flagsPayload =
      generationFlags && Object.values(generationFlags).some(Boolean)
        ? generationFlags
        : undefined;
    const isResearchRequest = Boolean(flagsPayload?.deep_research || flagsPayload?.web_search);
    const researchMode: 'light' | 'max' = flagsPayload?.deep_research ? 'max' : 'light';
    setScreenshotsLive(!isResearchRequest && !arenaMode);
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    let requestStart: number | null = null;
    let responseModel: string | null = null;

    try {
      if (arenaMode && isResearchRequest) {
        updateLastMessage({
          arena: {
            promptId: '',
            responseA: { content: '' },
            responseB: { content: '' },
            error: 'Arena mode does not support deep research yet.',
          },
        });
        return;
      }
      if (isResearchRequest) {
        await streamResearch(trimmedContent, researchMode, signal);
        return;
      }
      // Build request messages from current session
      const currentSession = getCurrentSession();
      const requestMessages = (currentSession?.messages || [])
        .slice(0, -1) // Exclude the placeholder
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      const userId = getUserId(user);
      const memoryEnabledSetting = memoryEnabled;
      const baselineAgentHeader = isCliAgentModel ? selectedAgent : undefined;

      if (arenaMode) {
        const arenaResponse = await requestArenaCompletion(
          {
            model: selectedModel,
            messages: requestMessages,
            stream: false,
            user_id: userId,
            enable_memory: memoryEnabledSetting,
            generation_flags: flagsPayload,
          },
          signal
        );
        updateLastMessage({
          arena: {
            promptId: arenaResponse.prompt_id,
            responseA: arenaResponse.response_a,
            responseB: arenaResponse.response_b,
            voted: false,
          },
        });
        return;
      }

      const handleResponse = (streamResponse: Response) => {
        const requestId =
          streamResponse.headers.get('x-request-id') || streamResponse.headers.get('X-Request-Id');
        if (requestId) {
          updateLastMessageMetadata({ requestId });
          logger.setRequestId(requestId);
        }
      };

      requestStart = performance.now();
      for await (const chunk of streamChatCompletion(
        {
          model: selectedModel,
          messages: requestMessages,
          stream: true,
          user_id: userId,
          enable_memory: memoryEnabledSetting,
          generation_flags: flagsPayload,
          debug: debugMode,
        },
        signal,
        handleResponse,
        { baselineAgent: baselineAgentHeader }
      )) {
        if ('type' in chunk && chunk.type === 'screenshot') {
          pushScreenshot(chunk.data);
          continue;
        }
        const completionChunk = chunk as ChatCompletionChunk;
        if (!responseModel && completionChunk.model) {
          responseModel = completionChunk.model;
          updateLastMessageMetadata({ model: responseModel });
        }
        const delta = completionChunk.choices[0]?.delta;
        if (delta?.janus?.event === 'screenshot') {
          const payload = coerceScreenshotPayload(delta.janus.payload);
          if (payload) {
            pushScreenshot(payload);
          }
          continue;
        }
        if (delta?.janus?.event === 'artifacts') {
          const artifacts = coerceArtifactsPayload(delta.janus.payload);
          if (artifacts.length > 0) {
            appendArtifacts(artifacts);
            if (currentSessionId) {
              void (async () => {
                const cached = await Promise.all(
                  artifacts.map((artifact) => cacheArtifact(currentSessionId, artifact))
                );
                appendArtifacts(cached);
              })();
            }
          }
          continue;
        }
        if (delta?.janus?.event === 'artifact') {
          const artifact = coerceArtifact(delta.janus.payload);
          if (artifact) {
            appendArtifacts([artifact]);
            if (currentSessionId) {
              void (async () => {
                const cached = await cacheArtifact(currentSessionId, artifact);
                appendArtifacts([cached]);
              })();
            }
          }
          continue;
        }
        if (delta) {
          // Filter out "(no content)" placeholder messages from Claude Code CLI
          const contentDelta = (delta.content || '').replace(/\(no content\)/g, '');
          const reasoningDelta = delta.reasoning_content || '';
          if (contentDelta || reasoningDelta) {
            appendToLastMessage(contentDelta, reasoningDelta);
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // User cancelled
      } else if (error instanceof RequestTimeoutError) {
        updateLastMessage({
          content: 'The task took too long and was stopped. Try breaking it into smaller steps.',
          reasoning_content: '',
        });
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
        if (arenaMode) {
          const sessionAtError = getCurrentSession();
          const lastArena = sessionAtError?.messages?.at(-1)?.arena;
          updateLastMessage({
            arena: {
              ...(lastArena || {
                promptId: '',
                responseA: { content: '' },
                responseB: { content: '' },
              }),
              error: 'Failed to load arena responses.',
            },
          });
        } else {
          appendToLastMessage('\n\n*Error: Failed to get response*', '');
        }
      }
    } finally {
      if (requestStart !== null) {
        updateLastMessageMetadata({ durationMs: Math.round(performance.now() - requestStart) });
      }
      setScreenshotsLive(false);
      setStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const getPreviousUserMessageText = useCallback(
    (fromIndex: number) => {
      for (let i = fromIndex - 1; i >= 0; i -= 1) {
        if (messages[i]?.role === 'user') {
          return getMessageText(messages[i].content).trim();
        }
      }
      return '';
    },
    [messages]
  );

  const handleRegenerate = useCallback(
    (prompt: string) => {
      if (isStreaming) return;
      const text = prompt.trim();
      if (!text) return;
      handleSend(text, []);
    },
    [handleSend, isStreaming]
  );

  const handleSelectPrompt = useCallback(
    (prompt: string) => {
      if (isStreaming) return;
      handleSend(prompt, []);
    },
    [handleSend, isStreaming]
  );

  const showQuickSuggestions =
    !isStreaming && (messages.length === 0 || messages[messages.length - 1]?.role === 'assistant');

  useEffect(() => {
    if (!initialMessage) return;
    if (autoSubmit && isStreaming) return;
    if (shareHandledRef.current === initialMessage) return;

    shareHandledRef.current = initialMessage;
    setPrefillMessage(initialMessage);

    if (autoSubmit) {
      const timeout = window.setTimeout(() => {
        handleSend(initialMessage, []);
        setPrefillMessage('');
      }, 500);

      return () => window.clearTimeout(timeout);
    }
  }, [autoSubmit, handleSend, initialMessage, isStreaming]);

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
      <div className="chat-body">
        <div className="chat-main">
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
              <Link href="/" className="chat-brand" title="Go to home" aria-label="Go to home">
                JANUS
              </Link>
            </div>

            <div className="chat-topbar-center">
              <div className="chat-session-info">
                <span className="chat-context">Session</span>
                <span className="chat-session-title">{session?.title || 'New chat'}</span>
              </div>
              <div className="chat-header-actions">
                {onNewChat && (
                  <button
                    type="button"
                    onClick={onNewChat}
                    className="chat-new-chat-btn hidden sm:flex"
                    aria-label="New chat"
                    title="New chat"
                  >
                    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                    </svg>
                  </button>
                )}
                <AgentStatusIndicator />
                {isCliAgentModel && (
                  <AgentSelector
                    agents={AGENT_OPTIONS}
                    selectedAgent={selectedAgent}
                    onSelect={setSelectedAgent}
                  />
                )}
                <ModelSelector
                  models={models.length ? models : [{ id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' }]}
                  selectedModel={selectedModel}
                  onSelect={setSelectedModel}
                />
              </div>
            </div>

            <div className="chat-topbar-right">
              <div className="chat-auth">
                {!authLoading && !isAuthenticated && (
                  <>
                    <button type="button" className="chat-signin-btn" onClick={() => signIn()}>
                      Sign in
                    </button>
                    <div className="chat-free-count hidden sm:block">
                      {freeChatsRemaining}/{FREE_CHAT_LIMIT} free
                    </div>
                  </>
                )}
                {isAuthenticated && user && (
                  <UserMenu userId={user.userId} username={user.username} onSignOut={signOut} />
                )}
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <ArenaToggle />
                <DebugToggle enabled={debugMode} onToggle={setDebugMode} />
                <MemoryToggle
                  enabled={memoryEnabled}
                  onOpen={() => setMemorySheetOpen(true)}
                  open={memorySheetOpen}
                />
              </div>
              <ChatOverflowMenu
                debugEnabled={debugMode}
                onDebugChange={setDebugMode}
                memoryEnabled={memoryEnabled}
                onMemoryToggle={() => setMemorySheetOpen(true)}
                onSessionsToggle={() => setSessionSheetOpen(true)}
                freeChatsRemaining={freeChatsRemaining}
                freeChatsLimit={FREE_CHAT_LIMIT}
                showFreeChats={!isAuthenticated}
              />
            </div>
          </div>

          <MemorySheet
            open={memorySheetOpen}
            onOpenChange={setMemorySheetOpen}
            memoryEnabled={memoryEnabled}
            onMemoryEnabledChange={(enabled) => {
              setMemoryEnabledState(enabled);
              setMemoryEnabled(enabled);
            }}
          />

          <SessionSheet
            open={sessionSheetOpen}
            onOpenChange={setSessionSheetOpen}
          />

          <SignInGateDialog
            open={signInGateOpen}
            onOpenChange={setSignInGateOpen}
            usedCount={freeChatsUsed}
            limit={FREE_CHAT_LIMIT}
            pendingMessage={pendingMessage}
          />
          <ShareModal
            isOpen={shareOpen}
            onClose={closeShare}
            conversationId={session?.id || ''}
            messages={messages}
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

          <div
            ref={messagesContainerRef}
            className="chat-messages-container px-6 py-6"
            aria-busy={isStreaming}
            data-testid="chat-messages"
          >
            <div className="max-w-4xl mx-auto flex min-h-full flex-col">
              <DeepResearchProgress stages={deepResearchStages} isActive={deepResearchActive} />
              <ScreenshotStream screenshots={screenshots} isLive={screenshotsLive} />
              {messages.length === 0 ? (
                <EmptyState onSelectPrompt={handleSelectPrompt} />
              ) : (
                <>
                  {messages.map((message, index) => {
                    const isLastMessage = index === messages.length - 1;
                    const isStreamingMessage = isStreaming && isLastMessage && message.role === 'assistant';
                    const isLastAssistantMessage = index === lastAssistantIndex;
                    const shouldAutoPlay = ttsAutoPlay && isLastAssistantMessage;
                    const regeneratePrompt =
                      message.role === 'assistant' ? getPreviousUserMessageText(index) : '';
                    const canRegenerate = message.role === 'assistant' && regeneratePrompt.length > 0;
                    return (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        showReasoning={showReasoning}
                        isStreaming={isStreamingMessage}
                        debugEnabled={debugMode}
                        autoPlay={shouldAutoPlay}
                        onAutoPlayHandled={shouldAutoPlay ? handleAutoPlayHandled : undefined}
                        onRegenerate={canRegenerate ? () => handleRegenerate(regeneratePrompt) : undefined}
                        onShare={openShare}
                      />
                    );
                  })}

                  {isStreaming && (
                    <div className="chat-streaming" role="status" aria-live="polite">
                      <span className="chat-streaming-dot" />
                      <span>Generating response</span>
                      <button onClick={handleCancel} className="chat-cancel">
                        Stop
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="chat-input-bottom px-6">
            <div className="max-w-4xl mx-auto">
              {!authLoading && !isAuthenticated && (
                <div className="chat-free-count-mobile sm:hidden">
                  {freeChatsRemaining}/{FREE_CHAT_LIMIT} free chats remaining today
                </div>
              )}
              <QuickSuggestions visible={showQuickSuggestions} onSelect={handleSelectPrompt} />
              <ChatInput onSend={handleSend} disabled={isStreaming} initialInput={prefillMessage} />
            </div>
          </div>
        </div>

        {debugMode && (
          <DebugPanel
            baseline={selectedModel}
            debugState={debugState}
            onClose={() => setDebugMode(false)}
          />
        )}
      </div>
    </div>
  );
}
