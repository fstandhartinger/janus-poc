'use client';

import Link from 'next/link';
import { Fragment, useMemo, useState } from 'react';

interface CompetitorDetails {
  suite: string;
  ttft: string;
  p95: string;
  tokens: string;
  notes: string;
}

interface CompetitorRow {
  rank: number;
  competitor: string;
  score: number;
  quality: number;
  speed: number;
  cost: number;
  streaming: number;
  modality: number;
  details: CompetitorDetails;
}

type SortKey = keyof Pick<
  CompetitorRow,
  'rank' | 'competitor' | 'score' | 'quality' | 'speed' | 'cost' | 'streaming' | 'modality'
>;

type SortDirection = 'asc' | 'desc';

const leaderboardData: CompetitorRow[] = [
  {
    rank: 1,
    competitor: 'baseline-v1',
    score: 78.4,
    quality: 82.1,
    speed: 71.2,
    cost: 85.0,
    streaming: 76.3,
    modality: 70.8,
    details: {
      suite: 'public/dev',
      ttft: '0.92s',
      p95: '4.2s',
      tokens: '1.2k avg',
      notes: 'Balanced across coding, research, and dialogue tasks.',
    },
  },
  {
    rank: 2,
    competitor: 'miner-alpha',
    score: 75.2,
    quality: 79.4,
    speed: 69.8,
    cost: 80.5,
    streaming: 72.0,
    modality: 74.1,
    details: {
      suite: 'public/dev',
      ttft: '1.04s',
      p95: '4.9s',
      tokens: '1.0k avg',
      notes: 'Strong multimodal handling with fast reroutes to tools.',
    },
  },
  {
    rank: 3,
    competitor: 'agent-x',
    score: 72.8,
    quality: 76.3,
    speed: 68.9,
    cost: 78.4,
    streaming: 69.5,
    modality: 71.2,
    details: {
      suite: 'public/dev',
      ttft: '1.21s',
      p95: '5.3s',
      tokens: '1.4k avg',
      notes: 'Great reasoning density with consistent streaming cadence.',
    },
  },
  {
    rank: 4,
    competitor: 'coyote-r1',
    score: 70.6,
    quality: 73.9,
    speed: 66.8,
    cost: 75.2,
    streaming: 68.1,
    modality: 67.4,
    details: {
      suite: 'public/dev',
      ttft: '1.34s',
      p95: '5.8s',
      tokens: '1.6k avg',
      notes: 'Excellent on long-form tasks, needs latency tuning.',
    },
  },
  {
    rank: 5,
    competitor: 'trailblazer',
    score: 68.9,
    quality: 71.5,
    speed: 64.7,
    cost: 74.0,
    streaming: 66.2,
    modality: 65.8,
    details: {
      suite: 'public/dev',
      ttft: '1.41s',
      p95: '6.2s',
      tokens: '1.3k avg',
      notes: 'Consistent cost profile with stable throughput.',
    },
  },
];

const columns: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: 'rank', label: 'Rank' },
  { key: 'competitor', label: 'Competitor' },
  { key: 'score', label: 'Score', numeric: true },
  { key: 'quality', label: 'Quality', numeric: true },
  { key: 'speed', label: 'Speed', numeric: true },
  { key: 'cost', label: 'Cost', numeric: true },
  { key: 'streaming', label: 'Streaming', numeric: true },
  { key: 'modality', label: 'Modality', numeric: true },
];

const formatScore = (value: number) => value.toFixed(1);

export function Leaderboard() {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [expanded, setExpanded] = useState<string[]>([]);

  const sortedData = useMemo(() => {
    const data = [...leaderboardData];
    const direction = sortDirection === 'asc' ? 1 : -1;
    data.sort((a, b) => {
      if (sortKey === 'competitor') {
        return a.competitor.localeCompare(b.competitor) * direction;
      }
      return (a[sortKey] - b[sortKey]) * direction;
    });
    return data;
  }, [sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection(key === 'rank' || key === 'competitor' ? 'asc' : 'desc');
  };

  const toggleExpanded = (competitor: string) => {
    setExpanded((prev) =>
      prev.includes(competitor)
        ? prev.filter((item) => item !== competitor)
        : [...prev, competitor]
    );
  };

  const lastUpdated = 'Updated 2 hours ago · 2025-01-22 14:32 UTC';

  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-8">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">Leaderboard</p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
              Current Competition Rankings
            </h2>
            <p className="text-[#9CA3AF] mt-3 max-w-2xl">
              Scores combine quality, speed, cost, streaming continuity, and modality
              handling. Sort any column to explore trade-offs across miners.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <span className="text-sm text-[#9CA3AF]">{lastUpdated}</span>
            <Link
              href="https://chutes-bench-runner-ui.onrender.com"
              target="_blank"
              rel="noreferrer"
              className="text-sm text-[#63D297] hover:underline"
            >
              View full benchmark results
            </Link>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-2">
              <thead>
                <tr>
                  {columns.map((column) => {
                    const sortState =
                      sortKey === column.key
                        ? sortDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none';
                    return (
                    <th
                      key={column.key}
                      scope="col"
                      aria-sort={sortState}
                      className="pb-2 text-xs uppercase tracking-[0.2em] text-[#9CA3AF]"
                    >
                      <button
                        type="button"
                        onClick={() => handleSort(column.key)}
                        className="flex items-center gap-2 hover:text-[#F3F4F6] transition"
                      >
                        {column.label}
                        {sortKey === column.key && (
                          <span className="text-[#63D297] text-sm">
                            {sortDirection === 'asc' ? '↑' : '↓'}
                          </span>
                        )}
                      </button>
                    </th>
                  );
                  })}
                </tr>
              </thead>
              <tbody>
                {sortedData.map((row) => {
                  const isExpanded = expanded.includes(row.competitor);
                  const detailsId = `details-${row.competitor}`;
                  return (
                    <Fragment key={row.competitor}>
                      <tr className="bg-[#0F172A]/40 rounded-lg">
                        <td className="py-3 px-3 font-semibold text-[#F3F4F6]">#{row.rank}</td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-3">
                            <span className="font-semibold text-[#F3F4F6]">{row.competitor}</span>
                            <button
                              type="button"
                              className="text-xs text-[#63D297] hover:underline"
                              aria-expanded={isExpanded}
                              aria-controls={detailsId}
                              onClick={() => toggleExpanded(row.competitor)}
                            >
                              {isExpanded ? 'Hide details' : 'View details'}
                            </button>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-[#F3F4F6]">{formatScore(row.score)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.quality)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.speed)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.cost)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.streaming)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.modality)}</td>
                      </tr>
                      {isExpanded && (
                        <tr id={detailsId} className="bg-[#0B111A]">
                          <td colSpan={8} className="px-4 pb-4">
                            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-[#D1D5DB]">
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">Suite</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.suite}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">TTFT</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.ttft}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">P95 latency</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.p95}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">Tokens</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.tokens}</p>
                              </div>
                            </div>
                            <p className="text-sm text-[#9CA3AF] mt-3">{row.details.notes}</p>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="md:hidden space-y-4">
            {sortedData.map((row) => {
              const isExpanded = expanded.includes(row.competitor);
              return (
                <div key={row.competitor} className="glass p-4 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm uppercase tracking-[0.2em] text-[#6B7280]">Rank</p>
                      <p className="text-xl font-semibold text-[#F3F4F6]">#{row.rank}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-[#9CA3AF]">Composite</p>
                      <p className="text-2xl font-semibold text-[#63D297]">{formatScore(row.score)}</p>
                    </div>
                  </div>
                  <div className="mt-3">
                    <p className="text-[#F3F4F6] font-semibold">{row.competitor}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-4 text-sm text-[#D1D5DB]">
                    <div>Quality: {formatScore(row.quality)}</div>
                    <div>Speed: {formatScore(row.speed)}</div>
                    <div>Cost: {formatScore(row.cost)}</div>
                    <div>Streaming: {formatScore(row.streaming)}</div>
                    <div>Modality: {formatScore(row.modality)}</div>
                  </div>
                  <button
                    type="button"
                    className="text-sm text-[#63D297] mt-4"
                    onClick={() => toggleExpanded(row.competitor)}
                    aria-expanded={isExpanded}
                  >
                    {isExpanded ? 'Hide details' : 'View details'}
                  </button>
                  {isExpanded && (
                    <div className="mt-4 space-y-2 text-sm text-[#9CA3AF]">
                      <div>Suite: {row.details.suite}</div>
                      <div>TTFT: {row.details.ttft}</div>
                      <div>P95 latency: {row.details.p95}</div>
                      <div>Tokens: {row.details.tokens}</div>
                      <p>{row.details.notes}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
