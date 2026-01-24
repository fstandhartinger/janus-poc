'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useChatStore } from '@/store/chat';

interface SidebarProps {
  isOpen?: boolean;
  isCollapsed?: boolean;
  onClose?: () => void;
  onToggleCollapse?: () => void;
}

export function Sidebar({
  isOpen = false,
  isCollapsed = false,
  onClose,
  onToggleCollapse,
}: SidebarProps) {
  const { sessions, currentSessionId, createSession, selectSession, deleteSession } =
    useChatStore();
  const [query, setQuery] = useState('');

  const filteredSessions = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    if (!trimmed) {
      return sessions;
    }
    return sessions.filter((session) => session.title.toLowerCase().includes(trimmed));
  }, [query, sessions]);

  const sidebarClasses = [
    'chat-sidebar',
    isOpen ? 'chat-sidebar-open' : 'chat-sidebar-closed',
    isCollapsed ? 'chat-sidebar-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <aside className={sidebarClasses}>
      <button
        type="button"
        onClick={() => onToggleCollapse?.()}
        className="chat-sidebar-toggle hidden lg:flex"
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
          {isCollapsed ? (
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7" />
          )}
        </svg>
      </button>
      <div className="px-5 pt-5 pb-4 border-b border-[#1F2937]">
        <Link
          href="/"
          onClick={onClose}
          className="chat-sidebar-item w-full flex items-center gap-2 mt-3"
          aria-label="Go to home"
          title="Go to home"
        >
          <svg
            viewBox="0 0 24 24"
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
            />
          </svg>
          <span className="chat-sidebar-hide-collapsed">Home</span>
        </Link>

        <button
          onClick={() => {
            createSession();
            onClose?.();
          }}
          className="mt-5 w-full flex items-center justify-center gap-2 rounded-xl bg-[#63D297] text-[#111827] px-4 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-0.5"
        >
          <span className="text-base leading-none">+</span>
          <span className="chat-sidebar-hide-collapsed">New Chat</span>
        </button>

        <button
          type="button"
          onClick={onClose}
          className="mt-3 w-full rounded-xl border border-[#1F2937] px-4 py-2 text-sm text-[#9CA3AF] lg:hidden"
        >
          Close
        </button>

        <div className="mt-4 search-input chat-sidebar-hide-collapsed">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search chats"
            aria-label="Search chats"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="text-xs uppercase tracking-[0.3em] text-[#6B7280] mb-3 chat-sidebar-hide-collapsed">
          Chats
        </div>
        {filteredSessions.length === 0 ? (
          <div className="text-sm text-[#6B7280] chat-sidebar-hide-collapsed">
            No conversations yet
          </div>
        ) : (
          <ul className="space-y-1 chat-session-list">
            {filteredSessions.map((session) => (
              <li key={session.id} className="relative group">
                <button
                  onClick={() => {
                    selectSession(session.id);
                    onClose?.();
                  }}
                  className={`chat-sidebar-item w-full justify-between ${
                    session.id === currentSessionId ? 'active' : ''
                  }`}
                >
                  <span className="truncate">{session.title}</span>
                </button>
                <button
                  onClick={() => deleteSession(session.id)}
                  className="absolute right-2 top-2.5 text-xs text-[#6B7280] opacity-0 group-hover:opacity-100 hover:text-[#FA5D19]"
                  title="Delete"
                  aria-label={`Delete ${session.title}`}
                >
                  x
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="px-5 py-4 border-t border-[#1F2937] text-xs text-[#6B7280] chat-sidebar-hide-collapsed">
        Janus PoC
      </div>

    </aside>
  );
}
