'use client';

import { useCallback, useEffect, useState } from 'react';
import { GATEWAY_URL } from '@/lib/api';
import { applyPreReleaseHeader } from '@/lib/preRelease';
import { useSessions, type SessionSummary, type StorageState } from '@/hooks/useSessions';
import { VNCViewer } from '@/components/VNCViewer';
import { SessionSaveDialog } from './SessionSaveDialog';

type SessionCaptureModalProps = {
  sessionToUpdate: SessionSummary | null;
  onDone: () => void;
  onCancel: () => void;
};

type SandboxInfo = {
  id: string;
  url: string;
  vncPort: number;
};

type CaptureState = 'creating' | 'connecting' | 'ready' | 'capturing' | 'saving' | 'error';

const SANDBOX_API_URL = `${GATEWAY_URL.replace(/\/+$/, '')}/api/sandbox`;

export function SessionCaptureModal({
  sessionToUpdate,
  onDone,
  onCancel,
}: SessionCaptureModalProps) {
  const { createSession, updateSession } = useSessions(false);
  const [state, setState] = useState<CaptureState>('creating');
  const [sandbox, setSandbox] = useState<SandboxInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [vncConnected, setVncConnected] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [capturedState, setCapturedState] = useState<StorageState | null>(null);
  const [detectedDomains, setDetectedDomains] = useState<string[]>([]);

  // Create sandbox on mount
  useEffect(() => {
    let mounted = true;

    const createSandbox = async () => {
      try {
        setState('creating');
        setError(null);

        const response = await fetch(`${SANDBOX_API_URL}/create`, {
          method: 'POST',
          credentials: 'include',
          headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            flavor: 'agent-ready',
            enableVnc: true,
            timeout: 600, // 10 minutes for session capture
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Failed to create sandbox');
        }

        const data = (await response.json()) as SandboxInfo;
        if (!mounted) return;

        setSandbox(data);
        setState('connecting');
      } catch (err) {
        if (!mounted) return;
        console.error('Failed to create sandbox:', err);
        setError(err instanceof Error ? err.message : 'Failed to create sandbox');
        setState('error');
      }
    };

    void createSandbox();

    return () => {
      mounted = false;
    };
  }, []);

  // Cleanup sandbox on unmount
  useEffect(() => {
    return () => {
      if (sandbox?.id) {
        // Fire and forget cleanup
        fetch(`${SANDBOX_API_URL}/${sandbox.id}`, {
          method: 'DELETE',
          credentials: 'include',
          headers: applyPreReleaseHeader(),
        }).catch(() => {});
      }
    };
  }, [sandbox?.id]);

  const handleVncConnect = useCallback(() => {
    setVncConnected(true);
    setState('ready');
  }, []);

  const handleVncDisconnect = useCallback(() => {
    setVncConnected(false);
    if (state === 'ready') {
      setState('connecting');
    }
  }, [state]);

  const handleCaptureSession = async () => {
    if (!sandbox) return;

    try {
      setState('capturing');
      setError(null);

      // Execute session capture command in sandbox
      const response = await fetch(`${SANDBOX_API_URL}/${sandbox.id}/capture-session`, {
        method: 'POST',
        credentials: 'include',
        headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to capture session');
      }

      const data = (await response.json()) as {
        storage_state: StorageState;
        detected_domains: string[];
      };

      setCapturedState(data.storage_state);
      setDetectedDomains(data.detected_domains || []);
      setShowSaveDialog(true);
      setState('ready');
    } catch (err) {
      console.error('Failed to capture session:', err);
      setError(err instanceof Error ? err.message : 'Failed to capture session');
      setState('ready');
    }
  };

  const handleSaveSession = async (name: string, description: string, domains: string[]) => {
    if (!capturedState) return;

    try {
      setState('saving');
      setError(null);

      if (sessionToUpdate) {
        await updateSession(sessionToUpdate.id, {
          name,
          description: description || undefined,
          storage_state: capturedState,
        });
      } else {
        await createSession({
          name,
          description: description || undefined,
          domains,
          storage_state: capturedState,
        });
      }

      setShowSaveDialog(false);
      onDone();
    } catch (err) {
      console.error('Failed to save session:', err);
      setError(err instanceof Error ? err.message : 'Failed to save session');
      setState('ready');
    }
  };

  const handleCancelSave = () => {
    setShowSaveDialog(false);
    setCapturedState(null);
    setDetectedDomains([]);
  };

  const isUpdating = Boolean(sessionToUpdate);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center session-capture-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={isUpdating ? 'Update browser session' : 'Capture browser session'}
    >
      <div className="session-capture-modal" onClick={(e) => e.stopPropagation()}>
        <div className="session-capture-header">
          <h2>{isUpdating && sessionToUpdate ? `Update: ${sessionToUpdate.name}` : 'Capture Browser Session'}</h2>
          <button
            type="button"
            className="session-capture-close"
            onClick={onCancel}
            aria-label="Cancel session capture"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
            </svg>
          </button>
        </div>

        <div className="session-capture-content">
          {state === 'creating' && (
            <div className="session-capture-loading">
              <span className="session-spinner" aria-hidden="true" />
              <p>Creating sandbox environment...</p>
            </div>
          )}

          {state === 'error' && (
            <div className="session-capture-error">
              <p>{error || 'An error occurred'}</p>
              <button type="button" onClick={onCancel} className="session-capture-retry">
                Close
              </button>
            </div>
          )}

          {(state === 'connecting' || state === 'ready' || state === 'capturing') && sandbox && (
            <>
              <div className="session-capture-instructions">
                <p>
                  <strong>1.</strong> Navigate to the website you want to authenticate with
                </p>
                <p>
                  <strong>2.</strong> Log in with your credentials
                </p>
                <p>
                  <strong>3.</strong> Click &quot;Capture Session&quot; when logged in
                </p>
              </div>

              <div className="session-capture-vnc-container">
                {!vncConnected && state === 'connecting' && (
                  <div className="session-capture-connecting">
                    <span className="session-spinner" aria-hidden="true" />
                    <p>Connecting to browser...</p>
                  </div>
                )}
                <VNCViewer
                  sandboxUrl={sandbox.url}
                  vncPort={sandbox.vncPort}
                  onConnect={handleVncConnect}
                  onDisconnect={handleVncDisconnect}
                />
              </div>

              {error && (
                <p className="session-capture-inline-error">{error}</p>
              )}

              <div className="session-capture-actions">
                <button
                  type="button"
                  className="session-capture-cancel"
                  onClick={onCancel}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="session-capture-save"
                  onClick={handleCaptureSession}
                  disabled={!vncConnected || state === 'capturing'}
                >
                  {state === 'capturing' ? (
                    <>
                      <span className="session-spinner-small" aria-hidden="true" />
                      Capturing...
                    </>
                  ) : (
                    'Capture Session'
                  )}
                </button>
              </div>
            </>
          )}

          {state === 'saving' && (
            <div className="session-capture-loading">
              <span className="session-spinner" aria-hidden="true" />
              <p>Saving session...</p>
            </div>
          )}
        </div>

        {showSaveDialog && capturedState && (
          <SessionSaveDialog
            defaultName={sessionToUpdate?.name || ''}
            defaultDescription={sessionToUpdate?.description || ''}
            detectedDomains={detectedDomains}
            existingDomains={sessionToUpdate?.domains}
            onSave={handleSaveSession}
            onCancel={handleCancelSave}
          />
        )}
      </div>
    </div>
  );
}
