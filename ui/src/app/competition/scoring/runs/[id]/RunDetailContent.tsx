'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ScoreRadar } from './ScoreRadar';
import { TaskResultsTable } from './TaskResultsTable';
import { StreamingMetrics } from './StreamingMetrics';
import { LeaderboardCompare } from './LeaderboardCompare';
import { applyPreReleaseHeader } from '@/lib/preRelease';

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

function parseEventData(event: MessageEvent) {
  try {
    return JSON.parse(event.data);
  } catch (parseError) {
    const match = event.data.match(/'error':\\s*'([^']+)'/);
    if (match) {
      return { error: match[1] };
    }
    return null;
  }
}

export function RunDetailContent({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRun = useCallback(async () => {
    const response = await fetch(`/api/scoring/runs/${runId}`, {
      headers: applyPreReleaseHeader(),
    });
    if (!response.ok) {
      if (response.status === 404) {
        setRun(null);
        setError('Run not found');
      }
      return;
    }

    const data = await response.json();
    setRun(data);
  }, [runId]);

  useEffect(() => {
    let isMounted = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        await fetchRun();
      } catch (fetchError) {
        if (isMounted) {
          setError('Unable to load run details.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      isMounted = false;
    };
  }, [fetchRun]);

  const runStatus = run?.status;

  useEffect(() => {
    if (!runStatus || runStatus === 'completed' || runStatus === 'failed') {
      return () => undefined;
    }

    let isActive = true;
    const eventSource = new EventSource(`/api/scoring/runs/${runId}/stream`);

    const startPolling = () => {
      if (pollingRef.current) return;
      pollingRef.current = setInterval(() => {
        fetchRun();
      }, 5000);
    };

    eventSource.addEventListener('progress', (event) => {
      const data = parseEventData(event);
      if (!data) return;
      setRun((prev) =>
        prev
          ? {
              ...prev,
              progress_current: data.current ?? prev.progress_current,
              progress_total: data.total ?? prev.progress_total,
              status: data.status ?? prev.status,
            }
          : prev
      );
    });

    eventSource.addEventListener('completed', (event) => {
      const data = parseEventData(event);
      if (data) {
        setRun(data);
      }
      eventSource.close();
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    });

    eventSource.addEventListener('failed', (event) => {
      const data = parseEventData(event);
      setRun((prev) =>
        prev
          ? {
              ...prev,
              status: 'failed',
              error: data?.error ?? prev.error ?? 'Run failed.',
            }
          : prev
      );
      eventSource.close();
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    });

    eventSource.onerror = () => {
      if (!isActive) return;
      eventSource.close();
      startPolling();
    };

    return () => {
      isActive = false;
      eventSource.close();
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [fetchRun, runId, runStatus]);

  if (loading) {
    return <div className="animate-pulse h-96 bg-white/10 rounded-lg" />;
  }

  if (error || !run) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-[#9CA3AF]">{error ?? 'Run not found'}</p>
        <Link href="/competition/scoring" className="text-[#63D297] hover:underline mt-4 inline-block">
          Back to Scoring
        </Link>
      </div>
    );
  }

  const isActive = run.status === 'running' || run.status === 'pending';

  return (
    <div className="space-y-8">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <Link
            href="/competition/scoring"
            className="text-[#9CA3AF] hover:text-[#F3F4F6] text-sm mb-2 inline-block"
          >
            Back to Scoring
          </Link>
          <h1 className="text-3xl font-semibold text-[#F3F4F6]">
            {run.suite.toUpperCase()} Suite Run
          </h1>
          <p className="text-[#9CA3AF] mt-1">
            {run.target_url || run.container_image || 'No target provided'}
          </p>
        </div>
        <StatusBadgeLarge status={run.status} />
      </div>

      {isActive && (
        <div className="glass-card p-6">
          <div className="flex justify-between items-center mb-3">
            <span className="text-[#F3F4F6] font-medium">Progress</span>
            <span className="text-[#9CA3AF]">
              {run.progress_current} / {run.progress_total || '?'} tasks
            </span>
          </div>
          <div
            className="w-full bg-white/10 rounded-full h-3"
            role="progressbar"
            aria-valuenow={run.progress_current}
            aria-valuemin={0}
            aria-valuemax={run.progress_total || undefined}
          >
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

      {run.error && (
        <div className="glass-card p-6 border-red-500/30 bg-red-500/5">
          <h3 className="text-red-400 font-medium mb-2">Error</h3>
          <pre className="text-sm text-red-300 whitespace-pre-wrap">{run.error}</pre>
        </div>
      )}

      {run.composite_score !== null && (
        <div className="grid lg:grid-cols-[1fr_1.5fr] gap-6">
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

      {run.composite_score !== null && (
        <LeaderboardCompare runScore={run.composite_score} />
      )}

      {run.status === 'completed' && (
        <StreamingMetrics runId={runId} />
      )}

      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-[#F3F4F6] mb-4">
          Task Results
        </h3>
        <TaskResultsTable runId={runId} autoLoad={run.status === 'completed'} />
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
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    completed: { bg: 'bg-green-500/10', text: 'text-green-400', label: 'OK' },
    running: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: 'RUN' },
    pending: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', label: 'PEND' },
    failed: { bg: 'bg-red-500/10', text: 'text-red-400', label: 'FAIL' },
  };

  const style = styles[status] || styles.pending;

  return (
    <span className={`px-4 py-2 rounded-lg ${style.bg} ${style.text} font-medium`}>
      {style.label} {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
