'use client';

import { useMemo, useState } from 'react';
import { useChatStore } from '@/store/chat';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
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
  ].join(' ');

  return (
    <aside className={sidebarClasses}>
      <div className="px-5 pt-5 pb-4 border-b border-[#1F2937]">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-[#6B7280]">Workspace</div>
            <div className="text-sm text-[#F3F4F6] mt-2 font-medium">Janus Auto</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-[#111726] border border-[#1F2937] flex items-center justify-center text-[#63D297]">
            J
          </div>
        </div>

        <button
          onClick={() => {
            createSession();
            onClose?.();
          }}
          className="mt-5 w-full flex items-center justify-center gap-2 rounded-xl bg-[#63D297] text-[#111827] px-4 py-2.5 text-sm font-semibold transition-transform hover:-translate-y-0.5"
        >
          <span className="text-base leading-none">+</span>
          New Chat
        </button>

        <button
          type="button"
          onClick={onClose}
          className="mt-3 w-full rounded-xl border border-[#1F2937] px-4 py-2 text-sm text-[#9CA3AF] lg:hidden"
        >
          Close
        </button>

        <div className="mt-4 search-input">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search chats"
            aria-label="Search chats"
          />
        </div>

        <div className="mt-4 space-y-1">
          <button type="button" className="chat-sidebar-item w-full">
            Library
          </button>
          <button type="button" className="chat-sidebar-item w-full">
            Agents
          </button>
          <button type="button" className="chat-sidebar-item w-full">
            Studio
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="text-xs uppercase tracking-[0.3em] text-[#6B7280] mb-3">
          Chats
        </div>
        {filteredSessions.length === 0 ? (
          <div className="text-sm text-[#6B7280]">No conversations yet</div>
        ) : (
          <ul className="space-y-1">
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

      <div className="px-5 py-4 border-t border-[#1F2937] text-xs text-[#6B7280]">
        Janus PoC
      </div>
    </aside>
  );
}
