/**
 * Chat state management using Zustand.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session, Message, MessageContent, TextContent, Artifact } from '@/types/chat';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface ChatState {
  sessions: Session[];
  currentSessionId: string | null;
  isStreaming: boolean;
  showReasoning: boolean;

  // Session actions
  createSession: () => string;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;

  // Message actions
  addMessage: (message: Omit<Message, 'id' | 'created_at'>) => void;
  updateLastMessage: (updates: Partial<Message>) => void;
  appendToLastMessage: (content: string, reasoning?: string) => void;
  appendArtifacts: (artifacts: Artifact[]) => void;

  // UI state
  setStreaming: (streaming: boolean) => void;
  toggleReasoning: () => void;

  // Helpers
  getCurrentSession: () => Session | undefined;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      isStreaming: false,
      showReasoning: true,

      createSession: () => {
        const id = generateId();
        const session: Session = {
          id,
          title: 'New Chat',
          messages: [],
          created_at: new Date(),
          updated_at: new Date(),
        };
        set((state) => ({
          sessions: [session, ...state.sessions],
          currentSessionId: id,
        }));
        return id;
      },

      selectSession: (id) => {
        set({ currentSessionId: id });
      },

      deleteSession: (id) => {
        set((state) => {
          const sessions = state.sessions.filter((s) => s.id !== id);
          const currentSessionId =
            state.currentSessionId === id
              ? sessions[0]?.id || null
              : state.currentSessionId;
          return { sessions, currentSessionId };
        });
      },

      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: generateId(),
          created_at: new Date(),
        };
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id === state.currentSessionId) {
              // Update session title from first user message
              let title = session.title;
              if (message.role === 'user' && session.messages.length === 0) {
                let titleSource = '';
                if (typeof message.content === 'string') {
                  titleSource = message.content;
                } else if (Array.isArray(message.content)) {
                  const textPart = message.content.find(
                    (part): part is TextContent => part.type === 'text'
                  );
                  titleSource = textPart?.text || '';
                }
                if (titleSource) {
                  title = titleSource.slice(0, 50) + (titleSource.length > 50 ? '...' : '');
                }
              }
              return {
                ...session,
                title,
                messages: [...session.messages, newMessage],
                updated_at: new Date(),
              };
            }
            return session;
          });
          return { sessions };
        });
      },

      updateLastMessage: (updates) => {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id === state.currentSessionId && session.messages.length > 0) {
              const messages = [...session.messages];
              const lastIndex = messages.length - 1;
              messages[lastIndex] = { ...messages[lastIndex], ...updates };
              return { ...session, messages, updated_at: new Date() };
            }
            return session;
          });
          return { sessions };
        });
      },

      appendToLastMessage: (content, reasoning) => {
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id === state.currentSessionId && session.messages.length > 0) {
              const messages = [...session.messages];
              const lastIndex = messages.length - 1;
              const lastMessage = messages[lastIndex];

              const currentContent =
                typeof lastMessage.content === 'string' ? lastMessage.content : '';
              const currentReasoning = lastMessage.reasoning_content || '';

              // Clean "(no content)" from both new and accumulated content
              const cleanContent = (currentContent + content)
                .replace(/\(no content\)/gi, '')
                .replace(/\s*\n\s*\n\s*\n+/g, '\n\n'); // Collapse multiple newlines

              // Deduplicate heartbeat messages in reasoning (keep only latest)
              let newReasoning = currentReasoning + (reasoning || '');
              // Replace consecutive "Agent working..." lines with just the latest
              newReasoning = newReasoning.replace(
                /(⏳ Agent working\.\.\. \(\d+s\)\n)+⏳ Agent working/g,
                '⏳ Agent working'
              );

              messages[lastIndex] = {
                ...lastMessage,
                content: cleanContent,
                reasoning_content: newReasoning,
              };
              return { ...session, messages, updated_at: new Date() };
            }
            return session;
          });
          return { sessions };
        });
      },

      appendArtifacts: (artifacts) => {
        if (!artifacts || artifacts.length === 0) return;
        set((state) => {
          const sessions = state.sessions.map((session) => {
            if (session.id === state.currentSessionId && session.messages.length > 0) {
              const messages = [...session.messages];
              const lastIndex = messages.length - 1;
              const lastMessage = messages[lastIndex];
              const existing = lastMessage.artifacts || [];
              const merged = new Map<string, Artifact>();
              existing.forEach((artifact) => merged.set(artifact.id, artifact));
              artifacts.forEach((artifact) => merged.set(artifact.id, artifact));
              messages[lastIndex] = {
                ...lastMessage,
                artifacts: Array.from(merged.values()),
              };
              return { ...session, messages, updated_at: new Date() };
            }
            return session;
          });
          return { sessions };
        });
      },

      setStreaming: (streaming) => {
        set({ isStreaming: streaming });
      },

      toggleReasoning: () => {
        set((state) => ({ showReasoning: !state.showReasoning }));
      },

      getCurrentSession: () => {
        const state = get();
        return state.sessions.find((s) => s.id === state.currentSessionId);
      },
    }),
    {
      name: 'janus-chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
