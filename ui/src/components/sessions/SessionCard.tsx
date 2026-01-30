'use client';

import type { SessionSummary } from '@/hooks/useSessions';

type SessionCardProps = {
  session: SessionSummary;
  onDelete: () => void;
  onUpdate: () => void;
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function SessionCard({ session, onDelete, onUpdate }: SessionCardProps) {
  const handleDelete = () => {
    if (window.confirm(`Delete session "${session.name}"? This cannot be undone.`)) {
      onDelete();
    }
  };

  const isExpired = session.expires_at && new Date(session.expires_at) < new Date();

  return (
    <div className={`session-card${isExpired ? ' session-card-expired' : ''}`}>
      <div className="session-card-header">
        <div className="session-card-name-row">
          <span className="session-card-name">{session.name}</span>
          {isExpired && <span className="session-card-expired-badge">Expired</span>}
        </div>
        <div className="session-card-actions">
          <button
            type="button"
            className="session-card-action"
            onClick={onUpdate}
            aria-label={`Update session ${session.name}`}
            title="Update session"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
          <button
            type="button"
            className="session-card-action session-card-action-delete"
            onClick={handleDelete}
            aria-label={`Delete session ${session.name}`}
            title="Delete session"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {session.description && (
        <p className="session-card-description">{session.description}</p>
      )}

      <div className="session-card-domains">
        {session.domains.map((domain) => (
          <span key={domain} className="session-card-domain">
            {domain}
          </span>
        ))}
      </div>

      <p className="session-card-date">Created: {formatDate(session.created_at)}</p>
    </div>
  );
}
