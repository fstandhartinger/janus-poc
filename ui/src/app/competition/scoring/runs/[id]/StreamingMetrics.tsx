'use client';

import { useEffect, useMemo, useState } from 'react';

interface RunSummary {
  run_id: string;
  composite_score: number;
  scores: Record<string, number>;
  metrics: {
    avg_latency_seconds?: number;
    avg_ttft_seconds?: number;
    total_tokens?: number;
    total_cost_usd?: number;
  };
  by_benchmark: Record<string, { score: number; passed: number; failed: number }>;
}

function formatMetric(value: number | undefined, suffix = '') {
  if (value === undefined || Number.isNaN(value)) return '-';
  return `${value.toFixed(2)}${suffix}`;
}

export function StreamingMetrics({ runId }: { runId: string }) {
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const fetchSummary = async () => {
      const response = await fetch(`/api/scoring/runs/${runId}/summary`);
      if (response.ok && isMounted) {
        setSummary(await response.json());
      }
      if (isMounted) {
        setLoading(false);
      }
    };

    fetchSummary();

    return () => {
      isMounted = false;
    };
  }, [runId]);

  const benchmarks = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.by_benchmark);
  }, [summary]);

  if (loading) {
    return <div className="glass-card p-6 animate-pulse h-32" />;
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="glass-card p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-[#F3F4F6]">Run Metrics</h3>
        <p className="text-sm text-[#9CA3AF]">
          Aggregated latency, throughput, and benchmark performance across this run.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Avg latency" value={formatMetric(summary.metrics.avg_latency_seconds, 's')} />
        <MetricCard label="Avg TTFT" value={formatMetric(summary.metrics.avg_ttft_seconds, 's')} />
        <MetricCard label="Total tokens" value={summary.metrics.total_tokens?.toFixed(0) ?? '-'} />
        <MetricCard label="Total cost" value={summary.metrics.total_cost_usd !== undefined ? `$${summary.metrics.total_cost_usd.toFixed(4)}` : '-'} />
      </div>

      {benchmarks.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm uppercase tracking-[0.2em] text-[#9CA3AF]">Benchmark summary</h4>
          <div className="grid sm:grid-cols-2 gap-3">
            {benchmarks.map(([benchmark, data]) => (
              <div key={benchmark} className="bg-white/5 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-[#F3F4F6] font-medium">{benchmark}</span>
                  <span className="text-[#63D297] font-mono">
                    {(data.score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="text-xs text-[#9CA3AF] mt-2">
                  {data.passed} passed - {data.failed} failed
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/5 rounded-lg p-4">
      <div className="text-xs text-[#9CA3AF] uppercase tracking-[0.2em]">{label}</div>
      <div className="text-2xl font-semibold text-[#F3F4F6] mt-2">{value}</div>
    </div>
  );
}
