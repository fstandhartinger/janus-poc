'use client';

import { useArena } from '@/hooks/useArena';

export function ArenaToggle() {
  const { arenaMode, setArenaMode } = useArena();
  const label = arenaMode ? 'Arena mode enabled' : 'Arena mode disabled';

  return (
    <div className="arena-toggle">
      <button
        type="button"
        role="switch"
        aria-checked={arenaMode}
        aria-label={label}
        className={`arena-toggle-switch${arenaMode ? ' is-on' : ''}`}
        onClick={() => setArenaMode(!arenaMode)}
      >
        <span className="arena-toggle-thumb" />
      </button>
      <div className="arena-toggle-text">
        <span className="arena-toggle-title">Arena</span>
        <span className="arena-toggle-caption">Blind A/B mode</span>
      </div>
    </div>
  );
}
