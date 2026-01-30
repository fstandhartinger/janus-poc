'use client';

import type { SessionSummary } from '@/hooks/useSessions';
import { SessionCard } from './SessionCard';

type SessionListProps = {
  sessions: SessionSummary[];
  onDelete: (id: string) => void;
  onUpdate: (session: SessionSummary) => void;
};

export function SessionList({ sessions, onDelete, onUpdate }: SessionListProps) {
  if (sessions.length === 0) {
    return (
      <div className="session-list-empty">
        <p>No browser sessions saved yet.</p>
        <p className="session-list-empty-hint">
          Capture a new session to enable agents to use your authenticated browser state.
        </p>
      </div>
    );
  }

  return (
    <div className="session-list">
      {sessions.map((session) => (
        <SessionCard
          key={session.id}
          session={session}
          onDelete={() => onDelete(session.id)}
          onUpdate={() => onUpdate(session)}
        />
      ))}
    </div>
  );
}
