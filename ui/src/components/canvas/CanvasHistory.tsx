'use client';

import { useCanvasStore, type CanvasVersion } from '@/store/canvas';

interface CanvasHistoryProps {
  versions: CanvasVersion[];
  currentVersionId: string;
  onClose: () => void;
}

export function CanvasHistory({ versions, currentVersionId, onClose }: CanvasHistoryProps) {
  const { restoreVersion } = useCanvasStore();

  const sortedVersions = [...versions].reverse();

  return (
    <div className="canvas-history" role="dialog" aria-label="Version history">
      <div className="canvas-history-header">
        <span>Version History</span>
        <button onClick={onClose} className="canvas-history-close" aria-label="Close history">
          X
        </button>
      </div>
      <div className="canvas-history-list">
        {sortedVersions.map((version) => (
          <div
            key={version.id}
            className={`canvas-history-item ${version.id === currentVersionId ? 'current' : ''}`}
          >
            <div className="canvas-history-info">
              <span className="canvas-history-desc">{version.description}</span>
              <span className="canvas-history-time">{formatTime(version.timestamp)}</span>
            </div>
            {version.id !== currentVersionId ? (
              <button
                onClick={() => restoreVersion(version.id)}
                className="canvas-history-restore"
              >
                Restore
              </button>
            ) : (
              <span className="canvas-history-current-badge">Current</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}
