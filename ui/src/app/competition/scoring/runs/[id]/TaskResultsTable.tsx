'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

interface TaskResult {
  id: string;
  task_id: string;
  benchmark: string;
  task_type: string | null;
  success: boolean;
  quality_score: number | null;
  latency_seconds: number | null;
  ttft_seconds: number | null;
  avg_tps: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  error: string | null;
}

const PAGE_SIZE = 8;

function formatPercent(value: number | null) {
  if (value === null || Number.isNaN(value)) return '-';
  return `${(value * 100).toFixed(1)}%`;
}

function formatSeconds(value: number | null) {
  if (value === null || Number.isNaN(value)) return '-';
  return `${value.toFixed(2)}s`;
}

function formatNumber(value: number | null) {
  if (value === null || Number.isNaN(value)) return '-';
  return value.toFixed(2);
}

export function TaskResultsTable({ runId, autoLoad = false }: { runId: string; autoLoad?: boolean }) {
  const [results, setResults] = useState<TaskResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const loadResults = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/scoring/runs/${runId}/results`);
      if (!response.ok) {
        throw new Error('Failed to load results');
      }
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load results');
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (autoLoad && results === null && !loading) {
      loadResults();
    }
  }, [autoLoad, results, loading, loadResults]);

  const totalPages = useMemo(() => {
    if (!results) return 0;
    return Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  }, [results]);

  const pageResults = useMemo(() => {
    if (!results) return [];
    const start = page * PAGE_SIZE;
    return results.slice(start, start + PAGE_SIZE);
  }, [page, results]);

  if (results === null && !loading) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-sm text-[#9CA3AF]">
          Task results can be large. Load them when you are ready to review details.
        </p>
        <button
          type="button"
          onClick={loadResults}
          className="px-4 py-2 rounded-lg bg-white/10 text-[#F3F4F6] hover:bg-white/20 transition"
        >
          Load task results
        </button>
      </div>
    );
  }

  if (loading) {
    return <div className="animate-pulse h-32 bg-white/10 rounded-lg" />;
  }

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>;
  }

  if (results && results.length === 0) {
    return <p className="text-sm text-[#9CA3AF]">No task results available yet.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto hidden lg:block">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              <th className="py-2">Benchmark</th>
              <th className="py-2">Task</th>
              <th className="py-2">Status</th>
              <th className="py-2 text-right">Quality</th>
              <th className="py-2 text-right">Latency</th>
              <th className="py-2 text-right">TTFT</th>
              <th className="py-2 text-right">TPS</th>
              <th className="py-2 text-right">Tokens</th>
              <th className="py-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {pageResults.map((result) => (
              <tr key={result.id} className="border-b border-white/5">
                <td className="py-3 text-[#F3F4F6] font-medium">
                  {result.benchmark}
                </td>
                <td className="py-3 text-sm text-[#9CA3AF]">{result.task_id}</td>
                <td className="py-3">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      result.success
                        ? 'bg-green-500/10 text-green-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}
                  >
                    {result.success ? 'Passed' : 'Failed'}
                  </span>
                </td>
                <td className="py-3 text-right font-mono text-[#F3F4F6]">
                  {formatPercent(result.quality_score)}
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF]">
                  {formatSeconds(result.latency_seconds)}
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF]">
                  {formatSeconds(result.ttft_seconds)}
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF]">
                  {formatNumber(result.avg_tps)}
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF]">
                  {result.total_tokens ?? '-'}
                </td>
                <td className="py-3 text-right font-mono text-[#9CA3AF]">
                  {result.cost_usd !== null ? `$${result.cost_usd.toFixed(4)}` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="space-y-4 lg:hidden">
        {pageResults.map((result) => (
          <div key={result.id} className="border border-white/10 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[#F3F4F6] font-medium">{result.benchmark}</p>
                <p className="text-xs text-[#6B7280]">{result.task_id}</p>
              </div>
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  result.success
                    ? 'bg-green-500/10 text-green-400'
                    : 'bg-red-500/10 text-red-400'
                }`}
              >
                {result.success ? 'Passed' : 'Failed'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-[#9CA3AF] mt-3">
              <div>
                <div className="uppercase tracking-[0.2em]">Quality</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {formatPercent(result.quality_score)}
                </div>
              </div>
              <div>
                <div className="uppercase tracking-[0.2em]">Latency</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {formatSeconds(result.latency_seconds)}
                </div>
              </div>
              <div>
                <div className="uppercase tracking-[0.2em]">TTFT</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {formatSeconds(result.ttft_seconds)}
                </div>
              </div>
              <div>
                <div className="uppercase tracking-[0.2em]">Tokens</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {result.total_tokens ?? '-'}
                </div>
              </div>
              <div>
                <div className="uppercase tracking-[0.2em]">TPS</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {formatNumber(result.avg_tps)}
                </div>
              </div>
              <div>
                <div className="uppercase tracking-[0.2em]">Cost</div>
                <div className="text-[#F3F4F6] font-mono text-sm">
                  {result.cost_usd !== null ? `$${result.cost_usd.toFixed(4)}` : '-'}
                </div>
              </div>
            </div>
            {result.error && (
              <div className="mt-3 text-xs text-red-400">{result.error}</div>
            )}
          </div>
        ))}
      </div>

      {results && results.length > PAGE_SIZE && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-[#9CA3AF]">
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((prev) => Math.max(0, prev - 1))}
              disabled={page === 0}
              className="px-3 py-1 rounded bg-white/10 text-[#F3F4F6] disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((prev) => Math.min(totalPages - 1, prev + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 rounded bg-white/10 text-[#F3F4F6] disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
