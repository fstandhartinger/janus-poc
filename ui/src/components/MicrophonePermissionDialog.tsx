'use client';

import { useEffect, useState } from 'react';

export function useMicrophonePermission() {
  const [permission, setPermission] = useState<PermissionState | 'unknown'>('unknown');

  useEffect(() => {
    if (!navigator?.permissions?.query) {
      return;
    }

    let active = true;

    navigator.permissions
      .query({ name: 'microphone' as PermissionName })
      .then((result) => {
        if (!active) return;
        setPermission(result.state);
        result.onchange = () => setPermission(result.state);
      })
      .catch(() => setPermission('unknown'));

    return () => {
      active = false;
    };
  }, []);

  const requestPermission = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setPermission('granted');
      return true;
    } catch {
      setPermission('denied');
      return false;
    }
  };

  return { permission, requestPermission };
}

export function MicrophonePermissionBanner() {
  const { permission, requestPermission } = useMicrophonePermission();
  const [dismissed, setDismissed] = useState(false);

  if (permission === 'granted' || dismissed) return null;

  return (
    <div
      className="mb-2 flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm"
      role="status"
      aria-live="polite"
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-amber-400 text-[10px] text-amber-400">
        !
      </span>
      <p className="text-ink-300">
        {permission === 'denied'
          ? 'Microphone access was denied. Enable it in your browser settings to use voice input.'
          : 'Enable microphone access for voice input.'}
      </p>
      {permission !== 'denied' && (
        <button
          type="button"
          onClick={requestPermission}
          className="ml-auto shrink-0 rounded bg-amber-500/20 px-3 py-1 text-amber-400 transition hover:bg-amber-500/30"
        >
          Enable
        </button>
      )}
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="text-ink-500 transition hover:text-ink-300"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
