'use client';

import type { MemoryRecord } from '@/hooks/useMemories';
import { MemoryCard } from './MemoryCard';

type MemoryListProps = {
  memories: MemoryRecord[];
  onEdit: (id: string, updates: Partial<MemoryRecord>) => Promise<void> | void;
  onDelete: (id: string) => Promise<void> | void;
};

export function MemoryList({ memories, onEdit, onDelete }: MemoryListProps) {
  if (memories.length === 0) {
    return (
      <p className="memory-empty">
        No memories yet. Start chatting and I&apos;ll remember important things!
      </p>
    );
  }

  return (
    <div className="memory-list">
      {memories.map((memory) => (
        <MemoryCard key={memory.id} memory={memory} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </div>
  );
}
