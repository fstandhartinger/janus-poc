'use client';

import { useEffect, useState } from 'react';
import { isMemoryEnabled, setMemoryEnabled } from '@/lib/memory';

type MemoryIconProps = {
  className?: string;
  slashed?: boolean;
};

const MemoryIcon = ({ className, slashed }: MemoryIconProps) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {/* Notebook with bookmark */}
    <path d="M4 4h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4V4z" />
    <path d="M4 4v18" strokeWidth="2" />
    <path d="M8 8h6" />
    <path d="M8 12h6" />
    <path d="M8 16h4" />
    {/* Bookmark tab */}
    <path d="M18 4h2v6l-1-1-1 1V4z" fill="currentColor" strokeWidth="0" />
    {slashed ? <line x1="3" y1="3" x2="21" y2="21" strokeWidth="2" /> : null}
  </svg>
);

export function MemoryToggle() {
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    setEnabled(isMemoryEnabled());
  }, []);

  const toggle = () => {
    const next = !enabled;
    setEnabled(next);
    setMemoryEnabled(next);
  };

  const title = enabled
    ? "Memory enabled - I'll remember important things"
    : 'Memory disabled - conversations are not remembered';

  return (
    <button
      type="button"
      onClick={toggle}
      className={`chat-memory-toggle${enabled ? ' is-enabled' : ''}`}
      title={title}
      aria-label={title}
      aria-pressed={enabled}
    >
      <MemoryIcon slashed={!enabled} className="w-5 h-5" />
    </button>
  );
}
