'use client';

type DebugToggleProps = {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
};

const BugIcon = ({ className }: { className?: string }) => (
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
    <path d="M9 9h6v6H9z" />
    <path d="M4 13h5" />
    <path d="M15 13h5" />
    <path d="M7 7l-3-3" />
    <path d="M17 7l3-3" />
    <path d="M12 4v2" />
    <path d="M12 17v3" />
  </svg>
);

export function DebugToggle({ enabled, onToggle }: DebugToggleProps) {
  const title = enabled ? 'Debug mode ON' : 'Debug mode OFF';

  return (
    <button
      type="button"
      onClick={() => onToggle(!enabled)}
      className={`chat-debug-toggle${enabled ? ' is-enabled' : ''}`}
      title={title}
      aria-label={title}
      aria-pressed={enabled}
    >
      <BugIcon className="w-5 h-5" />
    </button>
  );
}
