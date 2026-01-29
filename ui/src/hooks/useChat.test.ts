import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { useChat } from './useChat';
import { useChatStore } from '@/store/chat';

beforeEach(() => {
  useChatStore.setState({
    sessions: [],
    currentSessionId: null,
    isStreaming: false,
    showReasoning: true,
  });
  useChatStore.persist?.clearStorage?.();
});

describe('useChat', () => {
  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
  });

  it('adds user message on send', async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    await waitFor(() => {
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[0].content).toBe('Hello');
    });
  });
});
