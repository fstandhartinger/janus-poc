'use client';

import { useState } from 'react';
import { Sidebar, ChatArea } from '@/components';

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen chat-aurora-bg">
      <div className="chat-shell">
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <ChatArea onMenuClick={() => setSidebarOpen(true)} />
      </div>
    </div>
  );
}
