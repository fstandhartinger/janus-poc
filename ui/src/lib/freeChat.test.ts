import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  FREE_CHAT_LIMIT,
  incrementFreeChatCount,
  readFreeChatState,
  remainingFreeChats,
  setFreeChatCount,
} from './freeChat';

describe('freeChat', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-01-01T10:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('tracks free chats per day', () => {
    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT);

    incrementFreeChatCount();
    incrementFreeChatCount();

    const state = readFreeChatState();
    expect(state.count).toBe(2);
    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT - 2);
  });

  it('resets counts when the day changes', () => {
    incrementFreeChatCount();
    incrementFreeChatCount();
    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT - 2);

    vi.setSystemTime(new Date('2025-01-02T08:00:00Z'));
    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT);
  });

  it('caps and clamps counts', () => {
    setFreeChatCount(999);
    expect(remainingFreeChats()).toBe(0);

    setFreeChatCount(-2);
    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT);
  });

  it('handles storage errors gracefully', () => {
    vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });

    expect(remainingFreeChats()).toBe(FREE_CHAT_LIMIT);
  });
});
