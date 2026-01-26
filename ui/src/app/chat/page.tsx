'use client';

import { useCallback, useEffect, useState, useSyncExternalStore } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sidebar, ChatArea } from '@/components';
import { useCanvasStore } from '@/store/canvas';
import { useChatStore } from '@/store/chat';
import { useSettingsStore } from '@/store/settings';

const SIDEBAR_STORAGE_KEY = 'sidebar-collapsed';
const sidebarListeners = new Set<() => void>();

const notifySidebarCollapsed = () => {
  sidebarListeners.forEach((listener) => listener());
};

const readSidebarCollapsed = (): boolean => {
  if (typeof window === 'undefined') return false;
  const saved = localStorage.getItem(SIDEBAR_STORAGE_KEY);
  if (!saved) return false;
  try {
    return JSON.parse(saved) as boolean;
  } catch {
    localStorage.removeItem(SIDEBAR_STORAGE_KEY);
    return false;
  }
};

const subscribeSidebarCollapsed = (listener: () => void) => {
  sidebarListeners.add(listener);

  const handleStorage = (event: StorageEvent) => {
    if (event.key === SIDEBAR_STORAGE_KEY) {
      listener();
    }
  };

  if (typeof window !== 'undefined') {
    window.addEventListener('storage', handleStorage);
  }

  return () => {
    sidebarListeners.delete(listener);
    if (typeof window !== 'undefined') {
      window.removeEventListener('storage', handleStorage);
    }
  };
};

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const isCanvasOpen = useCanvasStore((state) => state.isOpen);
  const createSession = useChatStore((state) => state.createSession);
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTTSAutoPlay = useSettingsStore((state) => state.setTTSAutoPlay);
  const [sharePayload, setSharePayload] = useState<{
    initial: string;
    autoSubmit: boolean;
  } | null>(null);

  const sidebarCollapsed = useSyncExternalStore(
    subscribeSidebarCollapsed,
    readSidebarCollapsed,
    () => false
  );

  const toggleCollapse = useCallback(() => {
    if (typeof window === 'undefined') return;
    const next = !readSidebarCollapsed();
    localStorage.setItem('sidebar-collapsed', JSON.stringify(next));
    notifySidebarCollapsed();
  }, []);

  const openSidebar = useCallback(() => setSidebarOpen(true), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const handleNewChat = useCallback(() => createSession(), [createSession]);

  useEffect(() => {
    const initial = searchParams.get('initial');
    if (!initial) return;

    const autoSubmit = searchParams.get('autoSubmit') === 'true';
    const enableTTS = searchParams.get('tts') === 'true';

    setSharePayload({ initial, autoSubmit });
    if (enableTTS) {
      setTTSAutoPlay(true);
    }

    const url = new URL(window.location.href);
    url.searchParams.delete('initial');
    url.searchParams.delete('autoSubmit');
    url.searchParams.delete('tts');
    const query = url.searchParams.toString();
    router.replace(query ? `${url.pathname}?${query}` : url.pathname);
  }, [router, searchParams, setTTSAutoPlay]);

  return (
    <div className="chat-page chat-aurora-bg overflow-hidden flex flex-col">
      <main className={`chat-shell ${isCanvasOpen ? 'canvas-open' : ''}`} aria-label="Chat">
        <h1 className="sr-only">Janus Chat</h1>
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={closeSidebar}
            aria-hidden="true"
          />
        )}
        <Sidebar
          isOpen={sidebarOpen}
          isCollapsed={sidebarCollapsed}
          onClose={closeSidebar}
          onToggleCollapse={toggleCollapse}
        />
        <ChatArea
          onMenuClick={openSidebar}
          onNewChat={handleNewChat}
          initialMessage={sharePayload?.initial}
          autoSubmit={sharePayload?.autoSubmit}
        />
      </main>
    </div>
  );
}
