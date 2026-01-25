'use client';

import { useEffect, useMemo, useState } from 'react';

interface LeaderboardEntry {
  rank: number;
  competitor: {
    name: string;
    team: string | null;
  };
  scores: {
    composite?: number;
    quality?: number;
    speed?: number;
    cost?: number;
    streaming?: number;
    multimodal?: number;
  };
}

const CACHE_KEY = 'janus_scoring_leaderboard';
const CACHE_TTL = 5 * 60 * 1000;

export function LeaderboardCompare({ runScore }: { runScore: number }) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadLeaderboard = async () => {
      setLoading(true);
      setError(null);

      try {
        let cachedPayload: { timestamp: number; data: LeaderboardEntry[] } | null = null;
        if (typeof window !== 'undefined') {
          const cached = localStorage.getItem(CACHE_KEY);
          if (cached) {
            try {
              cachedPayload = JSON.parse(cached);
            } catch (parseError) {
              cachedPayload = null;
            }
          }
        }
        if (cachedPayload && Date.now() - cachedPayload.timestamp < CACHE_TTL) {
          setEntries(cachedPayload.data);
          setLoading(false);
          return;
        }

        const response = await fetch('/api/scoring/leaderboard?limit=8');
        if (!response.ok) {
          throw new Error('Failed to load leaderboard');
        }

        const data = await response.json();
        setEntries(data);
        if (typeof window !== 'undefined') {
          try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({ timestamp: Date.now(), data }));
          } catch (storageError) {
            // Cache is best-effort.
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load leaderboard');
      } finally {
        setLoading(false);
      }
    };

    loadLeaderboard();
  }, []);

  const projectedRank = useMemo(() => {
    if (entries.length === 0) return null;
    const scores = entries.map((entry) => entry.scores.composite ?? 0);
    const index = scores.findIndex((score) => runScore >= score);
    if (index === -1) return entries.length + 1;
    return index + 1;
  }, [entries, runScore]);

  if (loading) {
    return (
      <div className="glass-card p-6 animate-pulse">
        <div className="h-6 bg-white/10 rounded w-1/3" />
        <div className="h-12 bg-white/10 rounded mt-4" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-6">
        <p className="text-[#9CA3AF]">{error}</p>
      </div>
    );
  }

  if (entries.length === 0) return null;

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-[#F3F4F6]">Leaderboard Compare</h3>
          <p className="text-sm text-[#9CA3AF]">
            See how this run stacks up against the latest leaderboard entries.
          </p>
        </div>
        <div className="bg-white/5 rounded-lg px-4 py-2">
          <div className="text-xs text-[#9CA3AF] uppercase tracking-[0.2em]">Projected rank</div>
          <div className="text-2xl font-semibold text-[#63D297]">
            {projectedRank ? `#${projectedRank}` : '-'}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              <th className="py-2">Rank</th>
              <th className="py-2">Competitor</th>
              <th className="py-2 text-right">Composite</th>
              <th className="py-2 text-right hidden sm:table-cell">Quality</th>
              <th className="py-2 text-right hidden sm:table-cell">Speed</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.rank} className="border-b border-white/5">
                <td className="py-3 text-[#F3F4F6] font-medium">#{entry.rank}</td>
                <td className="py-3">
                  <div className="text-[#F3F4F6] font-medium">{entry.competitor.name}</div>
                  {entry.competitor.team && (
                    <div className="text-xs text-[#6B7280]">{entry.competitor.team}</div>
                  )}
                </td>
                <td className="py-3 text-right font-mono text-[#F3F4F6]">
                  {((entry.scores.composite ?? 0) * 100).toFixed(1)}%
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF] hidden sm:table-cell">
                  {((entry.scores.quality ?? 0) * 100).toFixed(1)}%
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF] hidden sm:table-cell">
                  {((entry.scores.speed ?? 0) * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
