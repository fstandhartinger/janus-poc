'use client';

import { useEffect, useState } from 'react';
import { fetchArenaLeaderboard } from '@/lib/api';

type ArenaEntry = {
  model: string;
  elo: number;
  wins: number;
  losses: number;
  ties: number;
  matches: number;
};

const formatWinRate = (entry: ArenaEntry) => {
  if (!entry.matches) return '—';
  const score = entry.wins + entry.ties * 0.5;
  return `${Math.round((score / entry.matches) * 100)}%`;
};

export function ArenaLeaderboard() {
  const [entries, setEntries] = useState<ArenaEntry[]>([]);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    let active = true;
    fetchArenaLeaderboard()
      .then((data) => {
        if (!active) return;
        setEntries(Array.isArray(data) ? data : []);
        setStatus('ready');
      })
      .catch(() => {
        if (!active) return;
        setStatus('error');
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section id="arena-leaderboard" className="py-16 lg:py-24">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 mb-8">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">User Preferences</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
            Arena Preference Ladder
          </h2>
          <p className="text-[#9CA3AF] max-w-2xl">
            Anonymous A/B votes fuel this live ranking. Models are randomized and revealed only after
            a decision, keeping comparisons honest.
          </p>
        </div>

        <div className="glass-card p-6 arena-leaderboard">
          {status === 'loading' && <p className="text-sm text-[#9CA3AF]">Loading votes...</p>}
          {status === 'error' && (
            <p className="text-sm text-[#FCA5A5]">Arena leaderboard is unavailable right now.</p>
          )}
          {status === 'ready' && entries.length === 0 && (
            <p className="text-sm text-[#9CA3AF]">No arena votes yet. Be the first to compare.</p>
          )}
          {status === 'ready' && entries.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-separate border-spacing-y-2">
                <thead>
                  <tr className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                    <th className="pb-2">Rank</th>
                    <th className="pb-2">Model</th>
                    <th className="pb-2">ELO</th>
                    <th className="pb-2">Matches</th>
                    <th className="pb-2">Win rate</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry, index) => (
                    <tr key={entry.model} className="bg-[#0F172A]/40 rounded-lg">
                      <td className="py-3 px-3 text-[#F3F4F6] font-semibold">#{index + 1}</td>
                      <td className="py-3 px-3 text-[#F3F4F6]">{entry.model}</td>
                      <td className="py-3 px-3 text-[#63D297]">{Math.round(entry.elo)}</td>
                      <td className="py-3 px-3 text-[#D1D5DB]">{entry.matches}</td>
                      <td className="py-3 px-3 text-[#D1D5DB]">{formatWinRate(entry)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
