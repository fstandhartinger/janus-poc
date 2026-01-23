'use client';

import { useEffect, useState } from 'react';
import { Sidebar, ChatArea } from '@/components';
import { Header } from '@/components/landing';

export default function ChatPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved) {
      try {
        setSidebarCollapsed(JSON.parse(saved));
      } catch {
        localStorage.removeItem('sidebar-collapsed');
      }
    }
  }, []);

  const toggleCollapse = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('sidebar-collapsed', JSON.stringify(newState));
  };

  if (!isMounted) {
    return <div className="min-h-screen chat-aurora-bg" aria-busy="true" />;
  }

  return (
    <div className="min-h-screen chat-aurora-bg flex flex-col">
      <Header />
      <div className="chat-shell flex-1">
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}
        <Sidebar
          isOpen={sidebarOpen}
          isCollapsed={sidebarCollapsed}
          onClose={() => setSidebarOpen(false)}
          onToggleCollapse={toggleCollapse}
        />
        <ChatArea onMenuClick={() => setSidebarOpen(true)} />
      </div>
    </div>
  );
}
