# Spec 56: Scoring UI Page

## Status: COMPLETE

## Context / Why

The competition page needs a dedicated scoring section where users can:
1. Submit their implementation for scoring
2. View live progress of scoring runs
3. See detailed results and breakdown by benchmark
4. Compare their scores with the leaderboard

This page integrates with the Scoring Service Backend (Spec 55) and provides a user-friendly interface for the Janus competition evaluation.

## Goals

- Create a `/competition/scoring` page in the Janus UI
- Add navigation link from the competition page
- Display run history with results
- Show real-time progress for active runs
- Provide detailed breakdown by benchmark
- Enable comparison with leaderboard entries

## Non-Goals

- Replacing the external chutes-bench-runner UI
- Implementing the scoring backend (see Spec 55)
- On-chain submission (future phase)

## Functional Requirements

### FR-1: Scoring Page Route

Create `/competition/scoring` page accessible from the competition section.

```tsx
// ui/src/app/competition/scoring/page.tsx

import { Header, Footer } from '@/components/landing';
import {
  ScoringHero,
  RunSubmitForm,
  ActiveRuns,
  RunHistory,
  RunDetail,
  LeaderboardCompare,
} from './components';

export default function ScoringPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <ScoringHero />
          <RunSubmitForm />
          <ActiveRuns />
          <RunHistory />
        </div>
      </main>
      <Footer />
    </div>
  );
}
```

### FR-2: Run Submit Form

```tsx
// ui/src/app/competition/scoring/components/RunSubmitForm.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

type TargetType = 'url' | 'container';
type Suite = 'quick' | 'full' | 'research' | 'tool_use' | 'multimodal' | 'streaming' | 'cost';

const SUITES: { value: Suite; label: string; description: string; duration: string }[] = [
  { value: 'quick', label: 'Quick Suite', description: 'Fast validation with core tests', duration: '~5 min' },
  { value: 'full', label: 'Full Suite', description: 'Complete evaluation across all benchmarks', duration: '~2 hrs' },
  { value: 'research', label: 'Research Only', description: 'Web search and synthesis tasks', duration: '~15 min' },
  { value: 'tool_use', label: 'Tool Use Only', description: 'Function calling and API integration', duration: '~10 min' },
  { value: 'multimodal', label: 'Multimodal Only', description: 'Image generation and vision tasks', duration: '~20 min' },
  { value: 'streaming', label: 'Streaming Only', description: 'TTFT, TPS, continuity metrics', duration: '~8 min' },
  { value: 'cost', label: 'Cost Only', description: 'Token efficiency evaluation', duration: '~5 min' },
];

export function RunSubmitForm() {
  const router = useRouter();
  const [targetType, setTargetType] = useState<TargetType>('url');
  const [targetUrl, setTargetUrl] = useState('');
  const [containerImage, setContainerImage] = useState('');
  const [suite, setSuite] = useState<Suite>('quick');
  const [model, setModel] = useState('deepseek-reasoner');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/scoring/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_type: targetType,
          target_url: targetType === 'url' ? targetUrl : undefined,
          container_image: targetType === 'container' ? containerImage : undefined,
          suite,
          model,
          subset_percent: 100,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create run');
      }

      const run = await response.json();
      router.push(`/competition/scoring/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="submit-run" className="glass-card p-8">
      <h2 className="text-2xl font-semibold text-[#F3F4F6] mb-6">
        Start a Scoring Run
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Type Selection */}
        <div className="space-y-3">
          <label className="text-sm text-[#9CA3AF]">Target Type</label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setTargetType('url')}
              className={`px-4 py-2 rounded-lg border transition ${
                targetType === 'url'
                  ? 'border-[#63D297] bg-[#63D297]/10 text-[#63D297]'
                  : 'border-white/10 text-[#9CA3AF] hover:border-white/20'
              }`}
            >
              API URL
            </button>
            <button
              type="button"
              onClick={() => setTargetType('container')}
              className={`px-4 py-2 rounded-lg border transition ${
                targetType === 'container'
                  ? 'border-[#63D297] bg-[#63D297]/10 text-[#63D297]'
                  : 'border-white/10 text-[#9CA3AF] hover:border-white/20'
              }`}
            >
              Container Image
            </button>
          </div>
        </div>

        {/* Target Input */}
        {targetType === 'url' ? (
          <div className="space-y-2">
            <label className="text-sm text-[#9CA3AF]">API Endpoint URL</label>
            <input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="http://localhost:8080 or https://your-api.example.com"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-[#F3F4F6] placeholder-[#6B7280]
                       focus:outline-none focus:border-[#63D297]/50"
              required
            />
            <p className="text-xs text-[#6B7280]">
              Must expose /v1/chat/completions and /health endpoints
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <label className="text-sm text-[#9CA3AF]">Container Image</label>
            <input
              type="text"
              value={containerImage}
              onChange={(e) => setContainerImage(e.target.value)}
              placeholder="ghcr.io/yourname/janus-implementation:latest"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-[#F3F4F6] placeholder-[#6B7280]
                       focus:outline-none focus:border-[#63D297]/50"
              required
            />
            <p className="text-xs text-[#6B7280]">
              Container will be run in a Sandy sandbox for evaluation
            </p>
          </div>
        )}

        {/* Suite Selection */}
        <div className="space-y-3">
          <label className="text-sm text-[#9CA3AF]">Benchmark Suite</label>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {SUITES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setSuite(s.value)}
                className={`p-4 rounded-lg border text-left transition ${
                  suite === s.value
                    ? 'border-[#63D297] bg-[#63D297]/10'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-medium text-[#F3F4F6]">{s.label}</span>
                  <span className="text-xs text-[#6B7280]">{s.duration}</span>
                </div>
                <p className="text-xs text-[#9CA3AF] mt-1">{s.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Model Selection */}
        <div className="space-y-2">
          <label className="text-sm text-[#9CA3AF]">Model (for tool metadata)</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                     text-[#F3F4F6] focus:outline-none focus:border-[#63D297]/50"
          >
            <option value="deepseek-reasoner">DeepSeek Reasoner</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-4 rounded-lg bg-[#63D297] text-[#0F1419] font-semibold
                   hover:bg-[#63D297]/90 disabled:opacity-50 disabled:cursor-not-allowed
                   transition"
        >
          {isSubmitting ? 'Starting Run...' : 'Start Scoring Run'}
        </button>
      </form>
    </section>
  );
}
```

### FR-3: Active Runs Display with Live Progress

```tsx
// ui/src/app/competition/scoring/components/ActiveRuns.tsx

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

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
    const fetchRuns = async () => {
      const response = await fetch('/api/scoring/runs?status=running&status=pending');
      if (response.ok) {
        setRuns(await response.json());
      }
    };

    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
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
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-3">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#63D297] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-[#63D297]"></span>
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

            {/* Progress Bar */}
            <div className="w-full bg-white/10 rounded-full h-2">
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
```

### FR-4: Run History Table

```tsx
// ui/src/app/competition/scoring/components/RunHistory.tsx

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

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

export function RunHistory() {
  const [runs, setRuns] = useState<HistoricalRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRuns = async () => {
      const response = await fetch('/api/scoring/runs?limit=20');
      if (response.ok) {
        setRuns(await response.json());
      }
      setLoading(false);
    };

    fetchRuns();
  }, []);

  if (loading) {
    return (
      <section className="glass-card p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-white/10 rounded w-1/4"></div>
          <div className="h-12 bg-white/10 rounded"></div>
          <div className="h-12 bg-white/10 rounded"></div>
          <div className="h-12 bg-white/10 rounded"></div>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <h3 className="text-xl font-semibold text-[#F3F4F6]">Run History</h3>

      <div className="glass-card overflow-hidden">
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
                <td className="p-4 text-sm text-[#9CA3AF] max-w-[200px] truncate">
                  {run.target_url || run.container_image}
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
                  {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
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
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/10 text-green-400',
    running: 'bg-blue-500/10 text-blue-400',
    pending: 'bg-yellow-500/10 text-yellow-400',
    failed: 'bg-red-500/10 text-red-400',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || styles.pending}`}>
      {status}
    </span>
  );
}
```

### FR-5: Run Detail Page

```tsx
// ui/src/app/competition/scoring/runs/[id]/page.tsx

import { Suspense } from 'react';
import { Header, Footer } from '@/components/landing';
import { RunDetailContent } from './RunDetailContent';

export default function RunDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <Suspense fallback={<RunDetailSkeleton />}>
            <RunDetailContent runId={params.id} />
          </Suspense>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function RunDetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 bg-white/10 rounded w-1/4"></div>
      <div className="glass-card p-8 space-y-4">
        <div className="h-20 bg-white/10 rounded"></div>
        <div className="h-40 bg-white/10 rounded"></div>
      </div>
    </div>
  );
}
```

### FR-6: Run Detail Content with Live Updates

```tsx
// ui/src/app/competition/scoring/runs/[id]/RunDetailContent.tsx

'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { ScoreRadar } from './ScoreRadar';
import { TaskResultsTable } from './TaskResultsTable';
import { StreamingMetrics } from './StreamingMetrics';

interface RunDetail {
  id: string;
  suite: string;
  target_type: string;
  target_url?: string;
  container_image?: string;
  status: string;
  progress_current: number;
  progress_total: number;
  composite_score: number | null;
  quality_score: number | null;
  speed_score: number | null;
  cost_score: number | null;
  streaming_score: number | null;
  multimodal_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

interface TaskResult {
  id: string;
  task_id: string;
  benchmark: string;
  task_type: string | null;
  success: boolean;
  quality_score: number | null;
  latency_seconds: number;
  ttft_seconds: number | null;
  avg_tps: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  error: string | null;
}

export function RunDetailContent({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [results, setResults] = useState<TaskResult[]>([]);
  const [loading, setLoading] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const fetchRun = async () => {
      const [runRes, resultsRes] = await Promise.all([
        fetch(`/api/scoring/runs/${runId}`),
        fetch(`/api/scoring/runs/${runId}/results`),
      ]);

      if (runRes.ok) {
        setRun(await runRes.json());
      }
      if (resultsRes.ok) {
        setResults(await resultsRes.json());
      }
      setLoading(false);
    };

    fetchRun();
  }, [runId]);

  // Live updates via SSE for running runs
  useEffect(() => {
    if (!run || run.status === 'completed' || run.status === 'failed') {
      return;
    }

    const eventSource = new EventSource(`/api/scoring/runs/${runId}/stream`);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setRun((prev) => prev ? { ...prev, ...data } : prev);
    });

    eventSource.addEventListener('completed', (e) => {
      const data = JSON.parse(e.data);
      setRun(data);
      eventSource.close();
    });

    eventSource.addEventListener('failed', (e) => {
      const data = JSON.parse(e.data);
      setRun((prev) => prev ? { ...prev, status: 'failed', error: data.error } : prev);
      eventSource.close();
    });

    return () => {
      eventSource.close();
    };
  }, [run?.status, runId]);

  if (loading) {
    return <div className="animate-pulse h-96 bg-white/10 rounded-lg"></div>;
  }

  if (!run) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-[#9CA3AF]">Run not found</p>
        <Link href="/competition/scoring" className="text-[#63D297] hover:underline mt-4 inline-block">
          Back to Scoring
        </Link>
      </div>
    );
  }

  const isActive = run.status === 'running' || run.status === 'pending';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/competition/scoring"
            className="text-[#9CA3AF] hover:text-[#F3F4F6] text-sm mb-2 inline-block"
          >
            ← Back to Scoring
          </Link>
          <h1 className="text-3xl font-semibold text-[#F3F4F6]">
            {run.suite.toUpperCase()} Suite Run
          </h1>
          <p className="text-[#9CA3AF] mt-1">
            {run.target_url || run.container_image}
          </p>
        </div>
        <StatusBadgeLarge status={run.status} />
      </div>

      {/* Progress (for active runs) */}
      {isActive && (
        <div className="glass-card p-6">
          <div className="flex justify-between items-center mb-3">
            <span className="text-[#F3F4F6] font-medium">Progress</span>
            <span className="text-[#9CA3AF]">
              {run.progress_current} / {run.progress_total || '?'} tasks
            </span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-3">
            <div
              className="bg-[#63D297] h-3 rounded-full transition-all duration-500"
              style={{
                width: run.progress_total
                  ? `${(run.progress_current / run.progress_total) * 100}%`
                  : '0%',
              }}
            />
          </div>
        </div>
      )}

      {/* Error (for failed runs) */}
      {run.error && (
        <div className="glass-card p-6 border-red-500/30 bg-red-500/5">
          <h3 className="text-red-400 font-medium mb-2">Error</h3>
          <pre className="text-sm text-red-300 whitespace-pre-wrap">{run.error}</pre>
        </div>
      )}

      {/* Scores Grid (for completed runs) */}
      {run.composite_score !== null && (
        <div className="grid lg:grid-cols-[1fr_1.5fr] gap-6">
          {/* Score Cards */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-[#F3F4F6] mb-4">
              Composite Score
            </h3>
            <div className="text-5xl font-bold text-[#63D297] mb-6">
              {(run.composite_score * 100).toFixed(1)}%
            </div>
            <div className="grid grid-cols-2 gap-4">
              <ScoreCard label="Quality" score={run.quality_score} weight="40%" />
              <ScoreCard label="Speed" score={run.speed_score} weight="20%" />
              <ScoreCard label="Cost" score={run.cost_score} weight="15%" />
              <ScoreCard label="Streaming" score={run.streaming_score} weight="15%" />
              <ScoreCard label="Multimodal" score={run.multimodal_score} weight="10%" />
            </div>
          </div>

          {/* Radar Chart */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-[#F3F4F6] mb-4">
              Score Breakdown
            </h3>
            <ScoreRadar
              quality={run.quality_score || 0}
              speed={run.speed_score || 0}
              cost={run.cost_score || 0}
              streaming={run.streaming_score || 0}
              multimodal={run.multimodal_score || 0}
            />
          </div>
        </div>
      )}

      {/* Streaming Metrics */}
      {run.status === 'completed' && (
        <StreamingMetrics runId={runId} />
      )}

      {/* Task Results */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-[#F3F4F6] mb-4">
          Task Results
        </h3>
        <TaskResultsTable results={results} />
      </div>
    </div>
  );
}

function ScoreCard({
  label,
  score,
  weight,
}: {
  label: string;
  score: number | null;
  weight: string;
}) {
  return (
    <div className="bg-white/5 rounded-lg p-3">
      <div className="text-xs text-[#6B7280] mb-1">
        {label} ({weight})
      </div>
      <div className="text-xl font-semibold text-[#F3F4F6]">
        {score !== null ? `${(score * 100).toFixed(1)}%` : '-'}
      </div>
    </div>
  );
}

function StatusBadgeLarge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; icon: string }> = {
    completed: { bg: 'bg-green-500/10', text: 'text-green-400', icon: '✓' },
    running: { bg: 'bg-blue-500/10', text: 'text-blue-400', icon: '●' },
    pending: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', icon: '○' },
    failed: { bg: 'bg-red-500/10', text: 'text-red-400', icon: '✕' },
  };

  const style = styles[status] || styles.pending;

  return (
    <span className={`px-4 py-2 rounded-lg ${style.bg} ${style.text} font-medium`}>
      {style.icon} {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
```

### FR-7: API Route Proxy

```tsx
// ui/src/app/api/scoring/runs/route.ts

import { NextRequest, NextResponse } from 'next/server';

const SCORING_SERVICE_URL = process.env.SCORING_SERVICE_URL || 'https://janus-scoring-service.onrender.com';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/runs${searchParams ? `?${searchParams}` : ''}`;

  const response = await fetch(url);
  const data = await response.json();

  return NextResponse.json(data, { status: response.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(`${SCORING_SERVICE_URL}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
```

### FR-8: Competition Page Navigation

Add a link to the scoring page from the competition page:

```tsx
// Add to ui/src/app/competition/components/HeroSection.tsx

<Link
  href="/competition/scoring"
  className="px-6 py-3 bg-[#63D297] text-[#0F1419] font-semibold rounded-lg
           hover:bg-[#63D297]/90 transition"
>
  Run Scoring
</Link>
```

Also add a sidebar navigation section in the competition page:

```tsx
// ui/src/app/competition/components/ScoringNav.tsx

import Link from 'next/link';

export function ScoringNav() {
  return (
    <section className="py-8 bg-[#111726]/50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-[#F3F4F6]">
              Ready to Test Your Implementation?
            </h3>
            <p className="text-[#9CA3AF] text-sm mt-1">
              Run the official benchmarks against your API or container
            </p>
          </div>
          <Link
            href="/competition/scoring"
            className="px-6 py-3 bg-[#63D297] text-[#0F1419] font-semibold rounded-lg
                     hover:bg-[#63D297]/90 transition"
          >
            Start Scoring Run
          </Link>
        </div>
      </div>
    </section>
  );
}
```

## Non-Functional Requirements

### NFR-1: Responsiveness

- All components responsive on mobile, tablet, desktop
- Tables collapse to cards on mobile
- Charts resize appropriately

### NFR-2: Real-time Updates

- Active runs show live progress via SSE
- Automatic refresh for pending/running state
- Graceful degradation if SSE unavailable

### NFR-3: Performance

- Lazy load task results
- Paginate large result sets
- Cache leaderboard data

### NFR-4: Accessibility

- All interactive elements keyboard accessible
- Color not sole indicator of status
- Screen reader friendly tables

## Acceptance Criteria

- [ ] `/competition/scoring` page renders
- [ ] Run submission form works
- [ ] Active runs show live progress
- [ ] Run history displays correctly
- [ ] Run detail page shows all scores
- [ ] Task results table works
- [ ] Mobile responsive
- [ ] Tests pass

## Files to Create

```
ui/src/app/competition/scoring/
├── page.tsx
├── components/
│   ├── ScoringHero.tsx
│   ├── RunSubmitForm.tsx
│   ├── ActiveRuns.tsx
│   ├── RunHistory.tsx
│   └── index.ts
├── runs/
│   └── [id]/
│       ├── page.tsx
│       ├── RunDetailContent.tsx
│       ├── ScoreRadar.tsx
│       ├── TaskResultsTable.tsx
│       └── StreamingMetrics.tsx

ui/src/app/api/scoring/
├── runs/
│   ├── route.ts
│   └── [id]/
│       ├── route.ts
│       ├── results/route.ts
│       └── stream/route.ts
```

## Related Specs

- `specs/55_scoring_service_backend.md` - Backend API this page consumes
- `specs/30_janus_benchmark_integration.md` - Benchmark definitions
- `specs/36_janus_bench_ui_section.md` - UI design patterns

NR_OF_TRIES: 1
