'use client';

import { useCallback, useEffect, useState } from 'react';
import { GATEWAY_URL } from '@/lib/api';
import { applyPreReleaseHeader } from '@/lib/preRelease';

/**
 * Browser session summary (metadata only, no storage state).
 */
export type SessionSummary = {
  id: string;
  name: string;
  description: string | null;
  domains: string[];
  expires_at: string | null;
  created_at: string;
  updated_at: string;
};

/**
 * Storage state in Playwright format.
 */
export type StorageState = {
  cookies: Array<Record<string, unknown>>;
  origins: Array<Record<string, unknown>>;
};

/**
 * Request body for creating a new session.
 */
export type SessionCreateRequest = {
  name: string;
  description?: string;
  domains: string[];
  storage_state: StorageState;
  expires_at?: string;
};

/**
 * Request body for updating a session.
 */
export type SessionUpdateRequest = {
  name?: string;
  description?: string;
  storage_state?: StorageState;
  expires_at?: string;
};

type UseSessionsResult = {
  sessions: SessionSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createSession: (request: SessionCreateRequest) => Promise<SessionSummary>;
  updateSession: (id: string, updates: SessionUpdateRequest) => Promise<SessionSummary>;
  deleteSession: (id: string) => Promise<void>;
  getSessionState: (id: string) => Promise<StorageState>;
};

const SESSIONS_API_BASE = `${GATEWAY_URL.replace(/\/+$/, '')}/api/sessions`;

/**
 * Hook for managing browser sessions.
 *
 * Sessions are user-scoped and require authentication.
 * The storage state is encrypted at rest in the session service.
 *
 * @param enabled Whether to fetch sessions (default true)
 */
export function useSessions(enabled = true): UseSessionsResult {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setSessions([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(SESSIONS_API_BASE, {
        cache: 'no-store',
        credentials: 'include',
        headers: applyPreReleaseHeader(),
      });
      if (!response.ok) {
        if (response.status === 401) {
          // User not authenticated - return empty list
          setSessions([]);
          return;
        }
        throw new Error(await response.text());
      }
      const data = (await response.json()) as { sessions?: SessionSummary[] };
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError('Unable to load browser sessions right now.');
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  const createSession = useCallback(async (request: SessionCreateRequest): Promise<SessionSummary> => {
    setError(null);
    const response = await fetch(SESSIONS_API_BASE, {
      method: 'POST',
      credentials: 'include',
      headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Failed to create session');
    }
    const newSession = (await response.json()) as SessionSummary;
    await refresh();
    return newSession;
  }, [refresh]);

  const updateSession = useCallback(
    async (id: string, updates: SessionUpdateRequest): Promise<SessionSummary> => {
      setError(null);
      const response = await fetch(`${SESSIONS_API_BASE}/${id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(updates),
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to update session');
      }
      const updated = (await response.json()) as SessionSummary;
      await refresh();
      return updated;
    },
    [refresh]
  );

  const deleteSession = useCallback(
    async (id: string) => {
      setError(null);
      const response = await fetch(`${SESSIONS_API_BASE}/${id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: applyPreReleaseHeader(),
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to delete session');
      }
      setSessions((prev) => prev.filter((s) => s.id !== id));
    },
    []
  );

  const getSessionState = useCallback(async (id: string): Promise<StorageState> => {
    const response = await fetch(`${SESSIONS_API_BASE}/${id}/state`, {
      credentials: 'include',
      headers: applyPreReleaseHeader(),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Failed to get session state');
    }
    const data = (await response.json()) as { storage_state: StorageState };
    return data.storage_state;
  }, []);

  useEffect(() => {
    if (!enabled) {
      setSessions([]);
      setIsLoading(false);
      return;
    }
    void refresh();
  }, [enabled, refresh]);

  return {
    sessions,
    isLoading,
    error,
    refresh,
    createSession,
    updateSession,
    deleteSession,
    getSessionState,
  };
}
