'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { applyPreReleaseHeader } from '@/lib/preRelease';

interface ActiveRun {
  id: string;
  suite: string;
  target_type: string;
  status: string;
  progress_current: number;
  progress_total: number;
  started_at: string;
}

export function ActiveRuns() {
  const [runs, setRuns] = useState<ActiveRun[]>([]);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchRuns = async () => {
      const response = await fetch('/api/scoring/runs?limit=20', {
        headers: applyPreReleaseHeader(),
        signal: controller.signal,
      });
      if (response.ok && isMounted) {
        const data = await response.json();
        const active = data.filter((run: ActiveRun) =>
          ['running', 'pending'].includes(run.status)
        );
        setRuns(active);
      }
    };

    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);

    return () => {
      isMounted = false;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  if (runs.length === 0) return null;

  return (
    <section className="space-y-4">
      <h3 className="text-xl font-semibold text-[#F3F4F6]">Active Runs</h3>

      <div className="space-y-3">
        {runs.map((run) => (
          <Link
            key={run.id}
            href={`/competition/scoring/runs/${run.id}`}
            className="block glass-card p-4 hover:border-[#63D297]/30 transition"
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="relative flex h-3 w-3" aria-hidden>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#63D297] opacity-75" />
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-[#63D297]" />
                </span>
                <span className="font-medium text-[#F3F4F6]">
                  {run.suite.toUpperCase()} Suite
                </span>
                <span className="text-xs px-2 py-1 rounded bg-white/5 text-[#9CA3AF]">
                  {run.target_type}
                </span>
              </div>
              <span className="text-sm text-[#9CA3AF]">
                {run.progress_current} / {run.progress_total || '?'} tasks
              </span>
            </div>

            <div className="w-full bg-white/10 rounded-full h-2" role="progressbar"
              aria-valuenow={run.progress_current}
              aria-valuemin={0}
              aria-valuemax={run.progress_total || undefined}
            >
              <div
                className="bg-[#63D297] h-2 rounded-full transition-all duration-500"
                style={{
                  width: run.progress_total
                    ? `${(run.progress_current / run.progress_total) * 100}%`
                    : '0%',
                }}
              />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
