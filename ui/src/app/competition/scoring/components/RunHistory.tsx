'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';

interface HistoricalRun {
  id: string;
  suite: string;
  target_type: string;
  target_url?: string;
  container_image?: string;
  status: string;
  composite_score: number | null;
  quality_score: number | null;
  speed_score: number | null;
  cost_score: number | null;
  streaming_score: number | null;
  multimodal_score: number | null;
  created_at: string;
  completed_at: string | null;
}

function formatRelativeTime(isoDate: string) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  if (typeof Intl === 'undefined' || !Intl.RelativeTimeFormat) {
    return date.toLocaleDateString();
  }

  const diffSeconds = Math.round((date.getTime() - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);

  const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 60 * 60 * 24 * 365],
    ['month', 60 * 60 * 24 * 30],
    ['week', 60 * 60 * 24 * 7],
    ['day', 60 * 60 * 24],
    ['hour', 60 * 60],
    ['minute', 60],
    ['second', 1],
  ];

  for (const [unit, secondsInUnit] of ranges) {
    if (absSeconds >= secondsInUnit || unit === 'second') {
      const value = Math.round(diffSeconds / secondsInUnit);
      return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(value, unit);
    }
  }

  return 'Just now';
}

export function RunHistory() {
  const [runs, setRuns] = useState<HistoricalRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchRuns = async () => {
      const response = await fetch('/api/scoring/runs?limit=20', {
        signal: controller.signal,
      });
      if (response.ok && isMounted) {
        setRuns(await response.json());
      }
      if (isMounted) {
        setLoading(false);
      }
    };

    fetchRuns();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  const mobileRuns = useMemo(() => runs, [runs]);

  if (loading) {
    return (
      <section className="glass-card p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-white/10 rounded w-1/4" />
          <div className="h-12 bg-white/10 rounded" />
          <div className="h-12 bg-white/10 rounded" />
          <div className="h-12 bg-white/10 rounded" />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <h3 className="text-xl font-semibold text-[#F3F4F6]">Run History</h3>

      <div className="glass-card overflow-hidden hidden md:block">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 text-sm text-[#9CA3AF] font-medium">Suite</th>
              <th className="text-left p-4 text-sm text-[#9CA3AF] font-medium">Target</th>
              <th className="text-left p-4 text-sm text-[#9CA3AF] font-medium">Status</th>
              <th className="text-right p-4 text-sm text-[#9CA3AF] font-medium">Composite</th>
              <th className="text-right p-4 text-sm text-[#9CA3AF] font-medium hidden lg:table-cell">Quality</th>
              <th className="text-right p-4 text-sm text-[#9CA3AF] font-medium hidden lg:table-cell">Speed</th>
              <th className="text-right p-4 text-sm text-[#9CA3AF] font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                className="border-b border-white/5 hover:bg-white/5 transition"
              >
                <td className="p-4">
                  <Link
                    href={`/competition/scoring/runs/${run.id}`}
                    className="text-[#63D297] hover:underline font-medium"
                  >
                    {run.suite.toUpperCase()}
                  </Link>
                </td>
                <td className="p-4 text-sm text-[#9CA3AF] max-w-[220px] truncate">
                  {run.target_url || run.container_image || '-'}
                </td>
                <td className="p-4">
                  <StatusBadge status={run.status} />
                </td>
                <td className="p-4 text-right">
                  {run.composite_score !== null ? (
                    <span className="font-mono text-[#F3F4F6]">
                      {(run.composite_score * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-[#6B7280]">-</span>
                  )}
                </td>
                <td className="p-4 text-right hidden lg:table-cell">
                  {run.quality_score !== null ? (
                    <span className="font-mono text-[#9CA3AF]">
                      {(run.quality_score * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-[#6B7280]">-</span>
                  )}
                </td>
                <td className="p-4 text-right hidden lg:table-cell">
                  {run.speed_score !== null ? (
                    <span className="font-mono text-[#9CA3AF]">
                      {(run.speed_score * 100).toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-[#6B7280]">-</span>
                  )}
                </td>
                <td className="p-4 text-right text-sm text-[#6B7280]">
                  {formatRelativeTime(run.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {runs.length === 0 && (
          <div className="p-8 text-center text-[#6B7280]">
            No scoring runs yet. Start your first run above!
          </div>
        )}
      </div>

      <div className="space-y-4 md:hidden">
        {mobileRuns.map((run) => (
          <Link
            key={run.id}
            href={`/competition/scoring/runs/${run.id}`}
            className="glass-card p-5 block"
          >
            <div className="flex items-center justify-between">
              <span className="text-[#63D297] font-semibold">
                {run.suite.toUpperCase()} Suite
              </span>
              <StatusBadge status={run.status} compact />
            </div>
            <p className="text-sm text-[#9CA3AF] mt-2 truncate">
              {run.target_url || run.container_image || '-'}
            </p>
            <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div>
                <div className="text-xs text-[#6B7280]">Composite</div>
                <div className="text-[#F3F4F6] font-mono">
                  {run.composite_score !== null ? `${(run.composite_score * 100).toFixed(1)}%` : '-'}
                </div>
              </div>
              <div>
                <div className="text-xs text-[#6B7280]">Speed</div>
                <div className="text-[#F3F4F6] font-mono">
                  {run.speed_score !== null ? `${(run.speed_score * 100).toFixed(1)}%` : '-'}
                </div>
              </div>
            </div>
            <div className="text-xs text-[#6B7280] mt-3">
              {formatRelativeTime(run.created_at)}
            </div>
          </Link>
        ))}
        {runs.length === 0 && (
          <div className="glass-card p-6 text-center text-[#6B7280]">
            No scoring runs yet. Start your first run above!
          </div>
        )}
      </div>
    </section>
  );
}

function StatusBadge({ status, compact = false }: { status: string; compact?: boolean }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/10 text-green-400',
    running: 'bg-blue-500/10 text-blue-400',
    pending: 'bg-yellow-500/10 text-yellow-400',
    failed: 'bg-red-500/10 text-red-400',
  };

  return (
    <span
      className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || styles.pending}`}
    >
      {compact ? status : status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
