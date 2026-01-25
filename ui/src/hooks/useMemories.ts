'use client';

import { useCallback, useEffect, useState } from 'react';
import { GATEWAY_URL } from '@/lib/api';

export type MemoryRecord = {
  id: string;
  caption: string;
  full_text: string;
  created_at: string;
};

type UseMemoriesResult = {
  memories: MemoryRecord[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  editMemory: (id: string, updates: Partial<MemoryRecord>) => Promise<void>;
  deleteMemory: (id: string) => Promise<void>;
  clearAll: () => Promise<void>;
};

const MEMORY_API_BASE = `${GATEWAY_URL.replace(/\/+$/, '')}/api/memories`;

export function useMemories(userId?: string, enabled = true): UseMemoriesResult {
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled || !userId) {
      setMemories([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${MEMORY_API_BASE}?user_id=${encodeURIComponent(userId)}`,
        { cache: 'no-store' }
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as { memories?: MemoryRecord[] };
      setMemories(Array.isArray(data.memories) ? data.memories : []);
    } catch (err) {
      console.error('Failed to fetch memories:', err);
      setError('Unable to load memories right now.');
    } finally {
      setIsLoading(false);
    }
  }, [enabled, userId]);

  const editMemory = useCallback(
    async (id: string, updates: Partial<MemoryRecord>) => {
      if (!userId) return;
      setError(null);
      const response = await fetch(`${MEMORY_API_BASE}/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, ...updates }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      await refresh();
    },
    [refresh, userId]
  );

  const deleteMemory = useCallback(
    async (id: string) => {
      if (!userId) return;
      setError(null);
      const response = await fetch(
        `${MEMORY_API_BASE}/${id}?user_id=${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setMemories((prev) => prev.filter((memory) => memory.id !== id));
    },
    [userId]
  );

  const clearAll = useCallback(async () => {
    if (!userId) return;
    if (!window.confirm('Delete all memories? This cannot be undone.')) return;
    setError(null);
    try {
      const response = await fetch(
        `${MEMORY_API_BASE}/clear?user_id=${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setMemories([]);
    } catch (err) {
      console.error('Failed to clear memories:', err);
      setError('Unable to clear memories right now.');
    }
  }, [userId]);

  useEffect(() => {
    if (!enabled) {
      setMemories([]);
      setIsLoading(false);
      return;
    }
    void refresh();
  }, [enabled, refresh]);

  return { memories, isLoading, error, refresh, editMemory, deleteMemory, clearAll };
}
