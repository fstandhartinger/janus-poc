'use client';

import { useMemo } from 'react';

import { useServiceHealth } from '@/hooks/useServiceHealth';

export function AgentStatusIndicator() {
  const { isAgentAvailable, isLoading, error } = useServiceHealth();

  const status = useMemo(() => {
    if (isLoading) {
      return { label: 'Checking status', className: 'is-loading' };
    }
    if (error) {
      return { label: 'Status unavailable', className: 'is-unknown' };
    }
    if (isAgentAvailable) {
      return { label: 'Full capabilities', className: 'is-available' };
    }
    return { label: 'Limited mode', className: 'is-limited' };
  }, [error, isAgentAvailable, isLoading]);

  return (
    <div className={`agent-status-indicator ${status.className}`} aria-live="polite">
      <span className="agent-status-dot" aria-hidden="true" />
      <span className="agent-status-label">{status.label}</span>
    </div>
  );
}
