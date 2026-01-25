'use client';

import { useEffect, useState } from 'react';
import { isMemoryEnabled, setMemoryEnabled } from '@/lib/memory';

type BrainIconProps = {
  className?: string;
  slashed?: boolean;
};

const BrainIcon = ({ className, slashed }: BrainIconProps) => (
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
    <path d="M12 18V5" />
    <path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4" />
    <path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5" />
    <path d="M17.997 5.125a4 4 0 0 1 2.526 5.77" />
    <path d="M18 18a4 4 0 0 0 2-7.464" />
    <path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517" />
    <path d="M6 18a4 4 0 0 1-2-7.464" />
    <path d="M6.003 5.125a4 4 0 0 0-2.526 5.77" />
    {slashed ? <line x1="4" y1="4" x2="20" y2="20" /> : null}
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
      <BrainIcon slashed={!enabled} className="w-5 h-5" />
    </button>
  );
}
