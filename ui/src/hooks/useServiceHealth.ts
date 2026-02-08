'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchWithRetry, GATEWAY_URL } from '@/lib/api';
import { applyPreReleaseHeader } from '@/lib/preRelease';

type ServiceHealthResponse = {
  status?: string;
  version?: string;
  sandbox_available?: boolean;
  features?: {
    agent_sandbox?: boolean;
    [key: string]: boolean | undefined;
  };
};

type UseServiceHealthResult = {
  isAgentAvailable: boolean | null;
  isLoading: boolean;
  error: string | null;
  lastCheckedAt: number | null;
  refresh: () => Promise<void>;
};

const HEALTH_URL = `${GATEWAY_URL.replace(/\/+$/, '')}/health`;
const DEFAULT_REFRESH_MS = 60000;

export function useServiceHealth(refreshIntervalMs = DEFAULT_REFRESH_MS): UseServiceHealthResult {
  const [isAgentAvailable, setIsAgentAvailable] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null);
  const refreshInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchWithRetry(
        HEALTH_URL,
        { cache: 'no-store', headers: applyPreReleaseHeader() },
        { retries: 1, timeoutMs: 8000 }
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as ServiceHealthResponse;
      const agentAvailable =
        typeof data.sandbox_available === 'boolean'
          ? data.sandbox_available
          : typeof data.features?.agent_sandbox === 'boolean'
          ? data.features.agent_sandbox
          : null;
      setIsAgentAvailable(agentAvailable);
      setLastCheckedAt(Date.now());
    } catch (err) {
      console.error('Failed to fetch service health:', err);
      setError('Unable to check agent status.');
      setIsAgentAvailable(null);
      setLastCheckedAt(Date.now());
    } finally {
      refreshInFlight.current = false;
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!refreshIntervalMs || refreshIntervalMs <= 0) return;
    const intervalId = window.setInterval(() => {
      void refresh();
    }, refreshIntervalMs);
    return () => window.clearInterval(intervalId);
  }, [refresh, refreshIntervalMs]);

  return { isAgentAvailable, isLoading, error, lastCheckedAt, refresh };
}
