'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

interface UserMenuProps {
  userId: string;
  username?: string | null;
  onSignOut: () => void;
}

export function UserMenu({ userId, username, onSignOut }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const displayName = username?.trim() ? `@${username}` : userId;
  const avatar = useMemo(() => {
    const label = (username?.trim() || userId).slice(0, 2).toUpperCase();
    return label;
  }, [userId, username]);

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (panelRef.current?.contains(target) || buttonRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div className="auth-user-menu">
      <button
        ref={buttonRef}
        type="button"
        className="auth-user-button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="auth-user-avatar">{avatar}</span>
        <span className="auth-user-name">{displayName}</span>
        <svg viewBox="0 0 20 20" className="auth-user-chevron" fill="currentColor" aria-hidden="true">
          <path d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.94a.75.75 0 0 1 1.08 1.04l-4.24 4.5a.75.75 0 0 1-1.08 0l-4.24-4.5a.75.75 0 0 1 .02-1.06z" />
        </svg>
      </button>

      {open && (
        <div ref={panelRef} className="auth-user-panel" role="menu">
          <div className="auth-user-label">Signed in as</div>
          <div className="auth-user-handle">{displayName}</div>
          <button type="button" className="auth-user-signout" onClick={onSignOut} role="menuitem">
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
