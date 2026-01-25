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
  miner: string;
  score: number;
  quality: number;
  speed: number;
  cost: number;
  streaming: number;
  modality: number;
  submitted: string;
  daysAtTop: number | null;
  details: CompetitorDetails;
}

type SortKey = keyof Pick<
  CompetitorRow,
  | 'rank'
  | 'competitor'
  | 'miner'
  | 'score'
  | 'quality'
  | 'speed'
  | 'cost'
  | 'streaming'
  | 'modality'
  | 'submitted'
  | 'daysAtTop'
>;

type SortDirection = 'asc' | 'desc';

const leaderboardData: CompetitorRow[] = [
  {
    rank: 1,
    competitor: 'your-janus-implementation',
    miner: '5Your...Key',
    score: 82.7,
    quality: 86.3,
    speed: 78.4,
    cost: 84.2,
    streaming: 80.1,
    modality: 78.5,
    submitted: '2025-01-20',
    daysAtTop: 4,
    details: {
      suite: 'public/dev',
      ttft: '0.78s',
      p95: '3.8s',
      tokens: '1.1k avg',
      notes: 'Could this be your implementation taking the crown? Submit and find out.',
    },
  },
  {
    rank: 2,
    competitor: 'quantum-rider',
    miner: '5G9a...C21',
    score: 79.4,
    quality: 82.8,
    speed: 74.2,
    cost: 81.5,
    streaming: 76.8,
    modality: 77.3,
    submitted: '2025-01-18',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '0.88s',
      p95: '4.2s',
      tokens: '1.0k avg',
      notes: 'Strong multimodal handling with efficient tool orchestration.',
    },
  },
  {
    rank: 3,
    competitor: 'baseline-n8n',
    miner: '5H2d...E9F',
    score: 76.2,
    quality: 79.5,
    speed: 71.8,
    cost: 78.9,
    streaming: 73.6,
    modality: 74.2,
    submitted: '2025-01-15',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '0.98s',
      p95: '4.6s',
      tokens: '1.2k avg',
      notes: 'Workflow-based baseline using n8n orchestration.',
    },
  },
  {
    rank: 4,
    competitor: 'baseline-cli-agent',
    miner: '5J7b...A10',
    score: 74.8,
    quality: 77.6,
    speed: 70.2,
    cost: 76.5,
    streaming: 72.1,
    modality: 71.8,
    submitted: '2025-01-12',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '1.04s',
      p95: '4.9s',
      tokens: '1.3k avg',
      notes: 'Reference CLI agent baseline with Aider integration.',
    },
  },
  {
    rank: 5,
    competitor: 'trailblazer',
    miner: '5K3e...D44',
    score: 72.5,
    quality: 75.2,
    speed: 68.4,
    cost: 74.8,
    streaming: 70.3,
    modality: 69.6,
    submitted: '2025-01-10',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '1.12s',
      p95: '5.1s',
      tokens: '1.4k avg',
      notes: 'Consistent performance across all benchmark categories.',
    },
  },
];

const columns: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: 'rank', label: 'Rank' },
  { key: 'competitor', label: 'Implementation' },
  { key: 'miner', label: 'Miner' },
  { key: 'score', label: 'Composite', numeric: true },
  { key: 'quality', label: 'Quality', numeric: true },
  { key: 'speed', label: 'Speed', numeric: true },
  { key: 'cost', label: 'Cost', numeric: true },
  { key: 'streaming', label: 'Streaming', numeric: true },
  { key: 'modality', label: 'Modality', numeric: true },
  { key: 'submitted', label: 'Submitted' },
  { key: 'daysAtTop', label: 'Days at #1', numeric: true },
];

const columnDefinitions = [
  { label: 'Rank', description: 'Current position.' },
  { label: 'Implementation', description: 'Name or identifier of the submission.' },
  { label: 'Miner', description: 'Bittensor hotkey (truncated).' },
  { label: 'Composite', description: 'Overall score on a 0-100 scale.' },
  { label: 'Quality', description: 'Aggregate task performance.' },
  { label: 'Speed', description: 'Latency and throughput score.' },
  { label: 'Cost', description: 'Resource efficiency score.' },
  { label: 'Streaming', description: 'Continuity and pacing score.' },
  { label: 'Modality', description: 'Multi-modal handling score.' },
  { label: 'Submitted', description: 'Date of submission.' },
  { label: 'Days at #1', description: 'Time at the top for the current leader.' },
];

const formatScore = (value: number) => value.toFixed(1);
const formatDaysAtTop = (value: number | null) => (value === null ? '—' : `${value} days`);

export function Leaderboard() {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [expanded, setExpanded] = useState<string[]>([]);
  const [columnsExpanded, setColumnsExpanded] = useState(false);

  const sortedData = useMemo(() => {
    const data = [...leaderboardData];
    const direction = sortDirection === 'asc' ? 1 : -1;
    data.sort((a, b) => {
      if (sortKey === 'competitor' || sortKey === 'miner') {
        return a[sortKey].localeCompare(b[sortKey]) * direction;
      }
      if (sortKey === 'submitted') {
        return (Date.parse(a.submitted) - Date.parse(b.submitted)) * direction;
      }
      if (sortKey === 'daysAtTop') {
        return ((a.daysAtTop ?? -1) - (b.daysAtTop ?? -1)) * direction;
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
    const isAscending = key === 'rank' || key === 'competitor' || key === 'miner' || key === 'submitted';
    setSortDirection(isAscending ? 'asc' : 'desc');
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
    <section id="leaderboard" className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-8">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">The Arena</p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
              Rodeo Rankings
            </h2>
            <p className="text-[#9CA3AF] mt-3 max-w-2xl">
              Composite scores blend task performance with production metrics like speed,
              cost, streaming continuity, and modality handling. Sort any column to
              explore trade-offs across implementations.
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
                        <td className="py-3 px-3 text-[#D1D5DB]">{row.miner}</td>
                        <td className="py-3 px-3 text-[#F3F4F6]">{formatScore(row.score)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.quality)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.speed)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.cost)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.streaming)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{formatScore(row.modality)}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">{row.submitted}</td>
                        <td className="py-3 px-3 text-[#D1D5DB]">
                          {formatDaysAtTop(row.daysAtTop)}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr id={detailsId} className="bg-[#0B111A]">
                          <td colSpan={11} className="px-4 pb-4">
                            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-[#D1D5DB]">
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Suite</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.suite}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">TTFT</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.ttft}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">P95 latency</p>
                                <p className="font-semibold text-[#F3F4F6]">{row.details.p95}</p>
                              </div>
                              <div>
                                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Tokens</p>
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
                      <p className="text-sm uppercase tracking-[0.2em] text-[#9CA3AF]">Rank</p>
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
                    <div>Miner: {row.miner}</div>
                    <div>Submitted: {row.submitted}</div>
                    <div>Days at #1: {formatDaysAtTop(row.daysAtTop)}</div>
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

        <div className="glass-card mt-6 overflow-hidden">
          <button
            type="button"
            onClick={() => setColumnsExpanded(!columnsExpanded)}
            className="w-full p-6 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
            aria-expanded={columnsExpanded}
            aria-controls="leaderboard-columns"
          >
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                Leaderboard columns
              </p>
              <p className="text-sm text-[#6B7280] mt-1">
                {columnsExpanded ? 'Click to collapse' : 'Click to see column definitions'}
              </p>
            </div>
            <svg
              className={`w-5 h-5 text-[#9CA3AF] transition-transform ${columnsExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {columnsExpanded && (
            <div id="leaderboard-columns" className="px-6 pb-6">
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                {columnDefinitions.map((column) => (
                  <div key={column.label} className="space-y-1">
                    <p className="text-[#F3F4F6] font-semibold">{column.label}</p>
                    <p className="text-[#9CA3AF]">{column.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
