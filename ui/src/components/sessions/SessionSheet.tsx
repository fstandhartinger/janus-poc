'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useSessions, type SessionSummary } from '@/hooks/useSessions';
import { SessionList } from './SessionList';
import { SessionCaptureModal } from './SessionCaptureModal';

type SessionSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function SessionSheet({ open, onOpenChange }: SessionSheetProps) {
  const { user, isAuthenticated } = useAuth();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const { sessions, isLoading, error, deleteSession, refresh } = useSessions(open && isAuthenticated);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [sessionToUpdate, setSessionToUpdate] = useState<SessionSummary | null>(null);

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (captureOpen) {
          setCaptureOpen(false);
        } else {
          event.preventDefault();
          onOpenChange(false);
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onOpenChange, open, captureOpen]);

  if (!open) return null;

  const handleStartCapture = () => {
    setSessionToUpdate(null);
    setCaptureOpen(true);
  };

  const handleUpdateSession = (session: SessionSummary) => {
    setSessionToUpdate(session);
    setCaptureOpen(true);
  };

  const handleCaptureDone = async () => {
    setCaptureOpen(false);
    setSessionToUpdate(null);
    await refresh();
  };

  const handleCaptureCancel = () => {
    setCaptureOpen(false);
    setSessionToUpdate(null);
  };

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex justify-end session-sheet-backdrop"
        role="dialog"
        aria-modal="true"
        aria-label="Browser session management"
        onClick={() => onOpenChange(false)}
        id="session-sheet"
      >
        <div
          className="session-sheet-panel"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="session-sheet-header">
            <div className="session-sheet-title">
              <span className="session-sheet-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                  />
                </svg>
              </span>
              <div>
                <h2>Browser Sessions</h2>
                <p>Manage authenticated browser sessions for agents</p>
              </div>
            </div>
            <button
              type="button"
              className="session-sheet-close"
              onClick={() => onOpenChange(false)}
              aria-label="Close session panel"
              ref={closeButtonRef}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
              </svg>
            </button>
          </div>

          <div className="session-sheet-content">
            {!isAuthenticated ? (
              <div className="session-auth-required">
                <p>Sign in to manage browser sessions.</p>
                <p className="session-auth-hint">
                  Browser sessions let agents use your authenticated state without logging in.
                </p>
              </div>
            ) : (
              <>
                <div className="session-info-box">
                  <p>
                    Capture a browser session by logging into a website, then save the cookies and
                    storage for agents to use later.
                  </p>
                </div>

                <div className="session-count-row">
                  <p>
                    {isLoading ? 'Loading sessions...' : `${sessions.length} sessions saved`}
                  </p>
                </div>

                {error && <p className="session-error">{error}</p>}

                {isLoading ? (
                  <div className="session-loading">
                    <span className="session-spinner" aria-hidden="true" />
                  </div>
                ) : (
                  <SessionList
                    sessions={sessions}
                    onDelete={deleteSession}
                    onUpdate={handleUpdateSession}
                  />
                )}

                <button
                  type="button"
                  className="session-capture-button"
                  onClick={handleStartCapture}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  Capture New Session
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {captureOpen && (
        <SessionCaptureModal
          sessionToUpdate={sessionToUpdate}
          onDone={handleCaptureDone}
          onCancel={handleCaptureCancel}
        />
      )}
    </>
  );
}
