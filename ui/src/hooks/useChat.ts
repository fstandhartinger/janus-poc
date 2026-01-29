import { useCallback, useMemo } from 'react';

import { useChatStore } from '@/store/chat';
import type { Message } from '@/types/chat';

export function useChat() {
  const sessions = useChatStore((state) => state.sessions);
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const createSession = useChatStore((state) => state.createSession);
  const addMessage = useChatStore((state) => state.addMessage);

  const messages = useMemo<Message[]>(() => {
    const session = sessions.find((item) => item.id === currentSessionId);
    return session?.messages ?? [];
  }, [sessions, currentSessionId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!currentSessionId) {
        createSession();
      }
      addMessage({ role: 'user', content });
    },
    [addMessage, createSession, currentSessionId]
  );

  return {
    messages,
    sendMessage,
  };
}
