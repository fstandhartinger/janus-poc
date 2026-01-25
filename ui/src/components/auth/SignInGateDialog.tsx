'use client';

import { useEffect, useRef } from 'react';

interface SignInGateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  usedCount: number;
  limit: number;
  pendingMessage?: string;
}

export function SignInGateDialog({
  open,
  onOpenChange,
  usedCount,
  limit,
  pendingMessage,
}: SignInGateDialogProps) {
  const signInButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    signInButtonRef.current?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onOpenChange(false);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onOpenChange, open]);

  if (!open) return null;

  const handleSignIn = () => {
    const returnTo = new URL(window.location.href);
    if (pendingMessage) {
      returnTo.searchParams.set('q', pendingMessage);
    }
    window.location.href = `/api/auth/login?returnTo=${encodeURIComponent(returnTo.toString())}`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Sign in to keep chatting"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="glass-card auth-gate-dialog w-full max-w-md p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="auth-gate-header">
          <div className="auth-gate-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7.5 21h9c1.657 0 3-1.343 3-3v-9c0-1.657-1.343-3-3-3h-9c-1.657 0-3 1.343-3 3v9c0 1.657 1.343 3 3 3z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 10.5h7.5M8.25 14.25h4.5"
              />
            </svg>
          </div>
          <div>
            <h2 className="auth-gate-title">Sign in to keep chatting</h2>
            <p className="auth-gate-subtitle">
              You&apos;ve used {usedCount}/{limit} free chats today. Sign in with your Chutes account to continue.
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <button
            ref={signInButtonRef}
            onClick={handleSignIn}
            className="auth-gate-button"
            type="button"
          >
            <span className="auth-gate-button-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6A2.25 2.25 0 0 0 5.25 5.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15"
                />
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 12h7.5m0 0L16.5 9m3 3-3 3" />
              </svg>
            </span>
            Sign in with Chutes
          </button>

          <p className="auth-gate-note">
            Don&apos;t have an account?{' '}
            <a
              href="https://chutes.ai/signup"
              target="_blank"
              rel="noopener noreferrer"
              className="auth-gate-link"
            >
              Create one for free
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
