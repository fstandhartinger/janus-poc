'use client';

import { useEffect, useState } from 'react';
import { applyPreReleaseHeader } from '@/lib/preRelease';

/**
 * Shows a banner when the scoring service is offline (e.g. suspended on
 * Render), so the page degrades gracefully instead of silently doing nothing.
 */
export function ScoringServiceNotice() {
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const check = async () => {
      try {
        const response = await fetch('/api/scoring/runs?limit=1', {
          headers: applyPreReleaseHeader(),
          signal: controller.signal,
          cache: 'no-store',
        });
        if (isMounted) {
          setUnavailable(response.status >= 500);
        }
      } catch {
        if (isMounted) {
          setUnavailable(true);
        }
      }
    };

    check();
    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  if (!unavailable) return null;

  return (
    <div
      role="status"
      className="glass-card border border-amber-400/30 bg-amber-500/10 p-4 flex items-start gap-3"
    >
      <span aria-hidden="true" className="mt-0.5 text-amber-300">
        <svg
          className="h-5 w-5"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 6a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 6Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
            clipRule="evenodd"
          />
        </svg>
      </span>
      <div>
        <p className="font-semibold text-amber-200">
          Scoring service temporarily offline
        </p>
        <p className="mt-1 text-sm text-amber-100/80">
          New scoring runs, run history and the scoring leaderboard are
          unavailable right now. The rest of Janus — including chat and the
          API — keeps working normally.
        </p>
      </div>
    </div>
  );
}
