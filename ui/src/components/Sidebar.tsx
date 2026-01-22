'use client';

import { useChatStore } from '@/store/chat';

export function Sidebar() {
  const { sessions, currentSessionId, createSession, selectSession, deleteSession } =
    useChatStore();

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={createSession}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
        >
          + New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-gray-400 text-sm">No conversations yet</div>
        ) : (
          <ul className="py-2">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => selectSession(session.id)}
                  className={`w-full px-4 py-3 text-left text-sm hover:bg-gray-800 transition-colors flex items-center justify-between group ${
                    session.id === currentSessionId ? 'bg-gray-800' : ''
                  }`}
                >
                  <span className="truncate flex-1">{session.title}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSession(session.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 ml-2"
                    title="Delete"
                  >
                    ×
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        Janus PoC
      </div>
    </div>
  );
}
