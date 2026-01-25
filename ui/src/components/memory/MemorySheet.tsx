'use client';

import { useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useMemories } from '@/hooks/useMemories';
import { getUserId } from '@/lib/userId';
import { MemoryList } from './MemoryList';

type MemorySheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  memoryEnabled: boolean;
  onMemoryEnabledChange: (enabled: boolean) => void;
};

export function MemorySheet({
  open,
  onOpenChange,
  memoryEnabled,
  onMemoryEnabledChange,
}: MemorySheetProps) {
  const { user } = useAuth();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const userId = getUserId(user);
  const { memories, isLoading, error, editMemory, deleteMemory, clearAll } = useMemories(
    userId,
    open
  );

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onOpenChange(false);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onOpenChange, open]);

  if (!open) return null;

  const handleToggle = () => {
    onMemoryEnabledChange(!memoryEnabled);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end memory-sheet-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Memory management"
      onClick={() => onOpenChange(false)}
      id="memory-sheet"
    >
      <div
        className="memory-sheet-panel"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="memory-sheet-header">
          <div className="memory-sheet-title">
            <span className="memory-sheet-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 4h6a4 4 0 0 1 4 4v2a3 3 0 0 1-2 2.83v3.17a3 3 0 0 1-3 3h-1"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 4a4 4 0 0 0-4 4v2a3 3 0 0 0 2 2.83V17a3 3 0 0 0 3 3h1"
                />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 8h2" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 16h2" />
              </svg>
            </span>
            <div>
              <h2>Memory</h2>
              <p>Manage what I remember about you</p>
            </div>
          </div>
          <button
            type="button"
            className="memory-sheet-close"
            onClick={() => onOpenChange(false)}
            aria-label="Close memory panel"
            ref={closeButtonRef}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>

        <div className="memory-sheet-content">
          <div className="memory-toggle-row">
            <div>
              <p className="memory-toggle-label">Enable Memory</p>
              <p className="memory-toggle-caption">Remember things from our conversations</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={memoryEnabled}
              className={`memory-toggle-switch${memoryEnabled ? ' is-on' : ''}`}
              onClick={handleToggle}
            >
              <span className="memory-toggle-thumb" />
            </button>
          </div>

          <div className="memory-divider" />

          <div className="memory-count-row">
            <p>
              {isLoading ? 'Loading memories...' : `${memories.length} memories stored`}
            </p>
            {memories.length > 0 && !isLoading && (
              <button type="button" onClick={clearAll} className="memory-clear-button">
                Clear All
              </button>
            )}
          </div>

          {error && <p className="memory-error">{error}</p>}

          {isLoading ? (
            <div className="memory-loading">
              <span className="memory-spinner" aria-hidden="true" />
            </div>
          ) : (
            <MemoryList memories={memories} onEdit={editMemory} onDelete={deleteMemory} />
          )}
        </div>
      </div>
    </div>
  );
}
