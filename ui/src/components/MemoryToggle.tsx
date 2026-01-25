'use client';

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
    <path d="M8 4h6a4 4 0 0 1 4 4v2a3 3 0 0 1-2 2.83v3.17a3 3 0 0 1-3 3h-1" />
    <path d="M8 4a4 4 0 0 0-4 4v2a3 3 0 0 0 2 2.83V17a3 3 0 0 0 3 3h1" />
    <path d="M9 8h2" />
    <path d="M9 12h3" />
    <path d="M9 16h2" />
    {slashed ? <line x1="3" y1="3" x2="21" y2="21" strokeWidth="2" /> : null}
  </svg>
);

type MemoryToggleProps = {
  enabled: boolean;
  onOpen: () => void;
  open?: boolean;
};

export function MemoryToggle({ enabled, onOpen, open }: MemoryToggleProps) {
  const title = enabled
    ? 'Memory enabled - manage memories'
    : 'Memory disabled - manage memories';

  return (
    <button
      type="button"
      onClick={onOpen}
      className={`chat-memory-toggle${enabled ? ' is-enabled' : ''}`}
      title={title}
      aria-label={title}
      aria-pressed={enabled}
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-controls="memory-sheet"
    >
      <MemoryIcon slashed={!enabled} className="w-5 h-5" />
    </button>
  );
}
