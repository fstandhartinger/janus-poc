'use client';

import { useEffect, useRef, useState } from 'react';
import RFB from '@novnc/novnc/lib/rfb';

interface VNCViewerProps {
  sandboxUrl: string;
  vncPort?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

const buildWsUrl = (sandboxUrl: string, vncPort?: number) => {
  const url = new URL(sandboxUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  if (vncPort) {
    url.port = String(vncPort);
  }
  url.pathname = '/vnc';
  url.search = '';
  url.hash = '';
  return url.toString();
};

export function VNCViewer({
  sandboxUrl,
  vncPort = 5900,
  onConnect,
  onDisconnect,
}: VNCViewerProps) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const rfbRef = useRef<RFB | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    let rfb: RFB | null = null;

    try {
      const wsUrl = buildWsUrl(sandboxUrl, vncPort);
      rfb = new RFB(canvasRef.current, wsUrl, {
        credentials: { password: '' },
      });

      rfb.addEventListener('connect', () => {
        setConnected(true);
        setError(null);
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (event: Event) => {
        setConnected(false);
        const detail = (event as CustomEvent<{ clean?: boolean }>).detail;
        if (detail?.clean) {
          onDisconnect?.();
        } else {
          setError('Connection lost');
        }
      });

      rfb.scaleViewport = true;
      rfb.resizeSession = true;
      rfbRef.current = rfb;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to connect: ${message}`);
    }

    return () => {
      if (rfb) {
        rfb.disconnect();
      }
      rfbRef.current = null;
    };
  }, [sandboxUrl, vncPort, onConnect, onDisconnect]);

  return (
    <div className="vnc-viewer">
      <div className="vnc-status">
        <span
          className={`vnc-indicator ${connected ? 'connected' : 'disconnected'}`}
        />
        <span>{connected ? 'Connected' : 'Disconnected'}</span>
      </div>

      {error && <div className="vnc-error">{error}</div>}

      <div
        ref={canvasRef}
        className="vnc-canvas"
        style={{ width: '100%', height: '600px' }}
      />
    </div>
  );
}
