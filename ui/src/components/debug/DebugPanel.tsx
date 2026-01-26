'use client';

import type { DebugState } from '@/types/debug';
import { DebugFlowDiagram } from './DebugFlowDiagram';
import { DebugLog } from './DebugLog';
import { DebugFiles } from './DebugFiles';

interface DebugPanelProps {
  baseline: string;
  debugState: DebugState;
  onClose: () => void;
}

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

const CloseIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M6 6l12 12" />
    <path d="M18 6l-12 12" />
  </svg>
);

export function DebugPanel({ baseline, debugState, onClose }: DebugPanelProps) {
  // Extract correlation ID from first event if available
  const correlationId =
    debugState.correlationId ||
    (debugState.events.length > 0 ? debugState.events[0].correlation_id : undefined);

  return (
    <div className="chat-debug-panel">
      <div className="chat-debug-header">
        <div className="chat-debug-title">
          <BugIcon className="w-4 h-4" />
          <span>Debug: {baseline}</span>
        </div>
        <button type="button" className="chat-debug-close" onClick={onClose} aria-label="Close debug panel">
          <CloseIcon className="w-3.5 h-3.5" />
        </button>
      </div>

      <DebugFlowDiagram
        baseline={baseline}
        currentStep={debugState.currentStep}
        highlightedNodes={debugState.activeNodes}
      />

      <DebugLog events={debugState.events} correlationId={correlationId} />

      <DebugFiles files={debugState.files} />
    </div>
  );
}
