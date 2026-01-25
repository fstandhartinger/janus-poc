'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

export type AuthUser = {
  userId: string;
  username?: string | null;
};

type AuthResponse = {
  user?: {
    id: string;
    username?: string | null;
  };
};

const fetchAuthMe = async (): Promise<AuthUser | null> => {
  const response = await fetch('/api/auth/me', {
    credentials: 'include',
    cache: 'no-store',
  });

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as AuthResponse;
  if (!payload.user?.id) {
    return null;
  }

  return {
    userId: payload.user.id,
    username: payload.user.username ?? null,
  };
};

export const useAuth = () => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchAuthMe();
      setUser(next);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signIn = useCallback((pendingMessage?: string) => {
    if (typeof window === 'undefined') return;
    const returnTo = new URL(window.location.href);
    if (pendingMessage) {
      returnTo.searchParams.set('q', pendingMessage);
    }
    window.location.href = `/api/auth/login?returnTo=${encodeURIComponent(returnTo.toString())}`;
  }, []);

  const signOut = useCallback(async () => {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading: loading,
      refresh,
      signIn,
      signOut,
    }),
    [loading, refresh, signIn, signOut, user]
  );

  return value;
};
