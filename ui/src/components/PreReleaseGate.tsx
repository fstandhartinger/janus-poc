"use client";

import { useCallback, useEffect, useState } from 'react';
import {
  PRE_RELEASE_HEADER,
  clearPreReleasePassword,
  getStoredPreReleasePassword,
  storePreReleasePassword,
} from '@/lib/preRelease';

type GateStatus = 'checking' | 'locked' | 'unlocked';

async function verifyPassword(password: string): Promise<boolean> {
  const response = await fetch('/api/pre-release/check', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      [PRE_RELEASE_HEADER]: password,
    },
    body: '{}',
    credentials: 'include',
  });
  return response.ok;
}

export default function PreReleaseGate() {
  const [status, setStatus] = useState<GateStatus>('checking');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const attemptUnlock = useCallback(async (candidate: string) => {
    setError(null);
    setStatus('checking');
    try {
      const ok = await verifyPassword(candidate);
      if (ok) {
        storePreReleasePassword(candidate);
        setStatus('unlocked');
        return;
      }
    } catch {
      // Ignore and fall through to error.
    }
    clearPreReleasePassword();
    setStatus('locked');
    setError('Incorrect password. Please try again.');
  }, []);

  useEffect(() => {
    let active = true;

    const checkGate = async () => {
      setError(null);
      setStatus('checking');
      const stored = getStoredPreReleasePassword();
      if (stored) {
        try {
          const ok = await verifyPassword(stored);
          if (!active) return;
          if (ok) {
            setStatus('unlocked');
            return;
          }
        } catch {
          // Ignore and fall through to locked state.
        }
        if (!active) return;
        clearPreReleasePassword();
        setStatus('locked');
        setError('Incorrect password. Please try again.');
        return;
      }

      try {
        const ok = await verifyPassword('');
        if (!active) return;
        if (ok) {
          setStatus('unlocked');
          return;
        }
      } catch {
        // Ignore and fall through to locked state.
      }

      if (!active) return;
      setStatus('locked');
    };

    checkGate().catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const isLocked = status !== 'unlocked';

  if (!isLocked) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/70 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 text-slate-900 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-600">
          Chutes pre-release Software
        </p>
        <h2 className="mt-3 text-2xl font-semibold">Enter access password</h2>
        <p className="mt-2 text-sm text-slate-600">
          This build is restricted. Enter the pre-release password to continue.
        </p>
        <form
          className="mt-6 flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (password.trim()) {
              attemptUnlock(password.trim());
            } else {
              setError('Password required.');
            }
          }}
        >
          <input
            type="password"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-base shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
            placeholder="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoFocus
          />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button
            type="submit"
            className="mt-2 inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
            disabled={status === 'checking'}
          >
            {status === 'checking' ? 'Checking...' : 'Unlock'}
          </button>
        </form>
      </div>
    </div>
  );
}
