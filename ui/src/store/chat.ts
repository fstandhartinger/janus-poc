/**
 * Chat state management using Zustand.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session, Message, MessageContent } from '@/types/chat';

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
      showReasoning: false,

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
              if (
                message.role === 'user' &&
                session.messages.length === 0 &&
                typeof message.content === 'string'
              ) {
                title = message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '');
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

              messages[lastIndex] = {
                ...lastMessage,
                content: currentContent + content,
                reasoning_content: currentReasoning + (reasoning || ''),
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
