'use client';

import { createPortal } from 'react-dom';
import type { CSSProperties, MouseEvent as ReactMouseEvent } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

const ExternalLinkIcon = ({ className }: { className?: string }) => (
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
    <path d="M14 3h7v7" />
    <path d="M21 3l-9 9" />
    <path d="M5 7v11a3 3 0 0 0 3 3h11" />
  </svg>
);

const DockIcon = ({ className }: { className?: string }) => (
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
    <path d="M7 3h10a2 2 0 0 1 2 2v6" />
    <path d="M17 17H7a2 2 0 0 1-2-2V9" />
    <path d="M8 21l4-4 4 4" />
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

const PANEL_MIN_WIDTH = 320;
const PANEL_MAX_WIDTH = 800;

const copyStyles = (source: Document, target: Document) => {
  source.querySelectorAll('link[rel="stylesheet"], style').forEach((node) => {
    target.head.appendChild(node.cloneNode(true));
  });
};

export function DebugPanel({ baseline, debugState, onClose }: DebugPanelProps) {
  // Extract correlation ID from first event if available
  const correlationId =
    debugState.correlationId ||
    (debugState.events.length > 0 ? debugState.events[0].correlation_id : undefined);
  const [panelWidth, setPanelWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const [isDetached, setIsDetached] = useState(false);
  const [detachedRoot, setDetachedRoot] = useState<HTMLElement | null>(null);
  const detachedWindowRef = useRef<Window | null>(null);

  const cleanupDetachedWindow = useCallback((shouldClose: boolean) => {
    const popup = detachedWindowRef.current;
    if (popup && shouldClose && !popup.closed) {
      popup.close();
    }
    detachedWindowRef.current = null;
    setDetachedRoot(null);
    setIsDetached(false);
  }, []);

  const handleDetach = useCallback(() => {
    if (typeof window === 'undefined') return;

    if (detachedWindowRef.current && !detachedWindowRef.current.closed) {
      detachedWindowRef.current.focus();
      return;
    }

    const width = 520;
    const height = 720;
    const left = window.screenX + Math.max(0, window.innerWidth - width - 40);
    const top = window.screenY + 40;
    const popup = window.open(
      '',
      'JanusDebugPanel',
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`,
    );

    if (!popup) return;
    detachedWindowRef.current = popup;
    popup.document.title = 'Janus Debug Panel';
    popup.document.body.innerHTML = '<div id="debug-root"></div>';
    popup.document.body.style.margin = '0';
    popup.document.body.style.background = '#0B111A';
    popup.document.documentElement.className = document.documentElement.className;
    popup.document.body.className = document.body.className;
    copyStyles(document, popup.document);

    const root = popup.document.getElementById('debug-root');
    if (root) {
      root.style.height = '100vh';
      setDetachedRoot(root);
      setIsDetached(true);
    }

    const handleUnload = () => {
      cleanupDetachedWindow(false);
    };
    popup.addEventListener('beforeunload', handleUnload, { once: true });
  }, [cleanupDetachedWindow]);

  const handleReattach = useCallback(() => {
    cleanupDetachedWindow(true);
  }, [cleanupDetachedWindow]);

  const handleClose = useCallback(() => {
    cleanupDetachedWindow(true);
    onClose();
  }, [cleanupDetachedWindow, onClose]);

  const handleMouseDown = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsResizing(true);
      const startX = event.clientX;
      const startWidth = panelWidth;
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const delta = startX - moveEvent.clientX;
        const nextWidth = Math.min(
          Math.max(startWidth + delta, PANEL_MIN_WIDTH),
          PANEL_MAX_WIDTH,
        );
        setPanelWidth(nextWidth);
      };

      const handleMouseUp = () => {
        setIsResizing(false);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [panelWidth],
  );

  useEffect(() => {
    return () => {
      cleanupDetachedWindow(true);
    };
  }, [cleanupDetachedWindow]);

  useEffect(() => {
    if (!isDetached) return;
    const popup = detachedWindowRef.current;
    if (!popup) return;
    const timer = window.setInterval(() => {
      if (!popup || popup.closed) {
        cleanupDetachedWindow(false);
      }
    }, 800);
    return () => window.clearInterval(timer);
  }, [isDetached, cleanupDetachedWindow]);

  const panelStyle = useMemo<CSSProperties | undefined>(() => {
    if (isDetached) return undefined;
    return { '--debug-panel-width': `${panelWidth}px` } as CSSProperties;
  }, [isDetached, panelWidth]);

  const panelContent = (
    <div
      className={`chat-debug-panel${isDetached ? ' is-detached' : ''}${isResizing ? ' is-resizing' : ''}`}
      style={panelStyle}
      data-testid="debug-panel"
    >
      <div className="chat-debug-header">
        <div className="chat-debug-title">
          <BugIcon className="w-4 h-4" />
          <span>Debug: {baseline}</span>
        </div>
        <div className="chat-debug-actions">
          <button
            type="button"
            className="chat-debug-action"
            onClick={isDetached ? handleReattach : handleDetach}
            aria-label={isDetached ? 'Dock debug panel' : 'Open debug panel in new window'}
            title={isDetached ? 'Dock panel' : 'Open in new window'}
          >
            {isDetached ? <DockIcon className="w-3.5 h-3.5" /> : <ExternalLinkIcon className="w-3.5 h-3.5" />}
          </button>
          <button type="button" className="chat-debug-action chat-debug-close" onClick={handleClose} aria-label="Close debug panel">
            <CloseIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {!isDetached && (
        <div
          className="debug-panel-resize-handle"
          onMouseDown={handleMouseDown}
          aria-hidden="true"
        />
      )}

      <DebugFlowDiagram
        baseline={baseline}
        currentStep={debugState.currentStep}
        highlightedNodes={debugState.activeNodes}
      />

      <DebugLog events={debugState.events} correlationId={correlationId} />

      <DebugFiles files={debugState.files} />
    </div>
  );

  if (isDetached && detachedRoot) {
    return (
      <>
        {createPortal(panelContent, detachedRoot)}
        <div className="chat-debug-panel chat-debug-panel-detached" style={panelStyle} data-testid="debug-panel">
          <div className="chat-debug-detached">
            <div className="chat-debug-detached-title">Debug panel is open in a separate window.</div>
            <div className="chat-debug-detached-actions">
              <button type="button" className="chat-debug-detached-btn" onClick={handleReattach}>
                Reattach
              </button>
              <button type="button" className="chat-debug-detached-btn secondary" onClick={handleClose}>
                Close
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  return panelContent;
}
