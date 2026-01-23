'use client';

import { Sidebar, ChatArea } from '@/components';
import { Header } from '@/components/landing';

export default function ChatPage() {
  return (
    <div className="flex flex-col h-screen bg-[#0B0F14]">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <ChatArea />
      </div>
    </div>
  );
}
