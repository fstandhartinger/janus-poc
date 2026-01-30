'use client';

import { useState, useRef, useEffect } from 'react';

interface ChatOverflowMenuProps {
  debugEnabled: boolean;
  onDebugChange: (enabled: boolean) => void;
  memoryEnabled: boolean;
  onMemoryToggle: () => void;
  freeChatsRemaining?: number;
  freeChatsLimit?: number;
  showFreeChats?: boolean;
}

const BugIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M9 9h6v6H9z" />
    <path d="M4 13h5" />
    <path d="M15 13h5" />
    <path d="M7 7l-3-3" />
    <path d="M17 7l3-3" />
    <path d="M12 4v2" />
    <path d="M12 17v3" />
  </svg>
);

const MemoryIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M8 4h6a4 4 0 0 1 4 4v2a3 3 0 0 1-2 2.83v3.17a3 3 0 0 1-3 3h-1" />
    <path d="M8 4a4 4 0 0 0-4 4v2a3 3 0 0 0 2 2.83V17a3 3 0 0 0 3 3h1" />
    <path d="M9 8h2" />
    <path d="M9 12h3" />
    <path d="M9 16h2" />
  </svg>
);

const HomeIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <polyline points="9 22 9 12 15 12 15 22" />
  </svg>
);

const MoreIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="currentColor"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="1.5" />
    <circle cx="6" cy="12" r="1.5" />
    <circle cx="18" cy="12" r="1.5" />
  </svg>
);

export function ChatOverflowMenu({
  debugEnabled,
  onDebugChange,
  memoryEnabled,
  onMemoryToggle,
  freeChatsRemaining,
  freeChatsLimit,
  showFreeChats,
}: ChatOverflowMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open]);

  return (
    <div ref={menuRef} className="chat-overflow-menu">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="chat-overflow-btn"
        aria-label="More options"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <MoreIcon className="w-4 h-4" />
      </button>

      {open && (
        <div className="chat-overflow-panel" role="menu">
          {showFreeChats && freeChatsRemaining !== undefined && freeChatsLimit !== undefined && (
            <div className="chat-overflow-info">
              {freeChatsRemaining}/{freeChatsLimit} free chats
            </div>
          )}

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              onDebugChange(!debugEnabled);
              setOpen(false);
            }}
            className="chat-overflow-item"
          >
            <BugIcon className="w-4 h-4" />
            <span className="chat-overflow-label">Debug mode</span>
            <span className={`chat-overflow-status ${debugEnabled ? 'is-on' : ''}`}>
              {debugEnabled ? 'ON' : 'OFF'}
            </span>
          </button>

          <button
            type="button"
            role="menuitem"
            onClick={() => {
              onMemoryToggle();
              setOpen(false);
            }}
            className="chat-overflow-item"
          >
            <MemoryIcon className="w-4 h-4" />
            <span className="chat-overflow-label">Memory</span>
            <span className={`chat-overflow-status ${memoryEnabled ? 'is-on' : ''}`}>
              {memoryEnabled ? 'ON' : 'OFF'}
            </span>
          </button>

          <a
            href="/"
            role="menuitem"
            className="chat-overflow-item"
            onClick={() => setOpen(false)}
          >
            <HomeIcon className="w-4 h-4" />
            <span className="chat-overflow-label">Go home</span>
          </a>
        </div>
      )}
    </div>
  );
}
