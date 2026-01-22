'use client';

import { Sidebar, ChatArea } from '@/components';

export default function Home() {
  return (
    <div className="flex h-screen bg-white dark:bg-gray-900">
      <Sidebar />
      <ChatArea />
    </div>
  );
}
