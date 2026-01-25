"""Performance analysis for Janus benchmark reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from janus_bench.models import BenchmarkReport, TaskResult


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics for a baseline."""

    # Composite scores
    composite_score: float
    quality_score: float
    speed_score: float
    cost_score: float
    streaming_score: float
    multimodal_score: float

    # Detailed metrics
    avg_ttft_ms: float
    p50_ttft_ms: float
    p95_ttft_ms: float

    avg_tps: float
    p50_tps: float
    p95_tps: float

    avg_latency_seconds: float
    p50_latency_seconds: float
    p95_latency_seconds: float

    continuity_score: float
    continuity_gap_count: int

    total_tokens: int
    avg_tokens_per_task: float
    total_cost_usd: float
    avg_cost_per_task: float

    # Task breakdown
    tasks_by_benchmark: dict[str, dict]
    failed_tasks: list[dict]
    slow_tasks: list[dict]


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    if len(values_sorted) == 1:
        return values_sorted[0]
    rank = (len(values_sorted) - 1) * percentile
    low = int(rank)
    high = min(low + 1, len(values_sorted) - 1)
    if low == high:
        return values_sorted[low]
    weight = rank - low
    return values_sorted[low] + (values_sorted[high] - values_sorted[low]) * weight


def _load_report(report_path: str) -> BenchmarkReport:
    path = Path(report_path)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    for result in payload.get("results", []):
        quality_score = result.get("quality_score")
        if isinstance(quality_score, (int, float)):
            result["quality_score"] = max(0.0, min(1.0, float(quality_score)))
    return BenchmarkReport(**payload)


def _collect_ttft_ms(results: list[TaskResult]) -> list[float]:
    ttft_ms: list[float] = []
    for result in results:
        metrics = result.streaming_metrics
        if metrics and metrics.ttft_seconds is not None:
            ttft_ms.append(metrics.ttft_seconds * 1000)
    return ttft_ms


def _collect_tps(results: list[TaskResult]) -> list[float]:
    tps_values: list[float] = []
    for result in results:
        if result.tokens_per_second is not None:
            tps_values.append(float(result.tokens_per_second))
            continue
        metrics = result.streaming_metrics
        if metrics and metrics.avg_tps is not None:
            tps_values.append(float(metrics.avg_tps))
    return tps_values


def _collect_latency(results: list[TaskResult]) -> list[float]:
    return [float(result.latency_seconds) for result in results]


def _collect_continuity(results: list[TaskResult]) -> tuple[list[float], int]:
    continuity_scores: list[float] = []
    gap_count = 0
    for result in results:
        metrics = result.streaming_metrics
        if not metrics:
            continue
        if metrics.continuity_score is not None:
            continuity_scores.append(float(metrics.continuity_score))
        if metrics.continuity_gap_count is not None:
            gap_count += int(metrics.continuity_gap_count)
    return continuity_scores, gap_count


def _group_by_benchmark(results: list[TaskResult]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[TaskResult]] = {}
    for result in results:
        grouped.setdefault(result.benchmark, []).append(result)

    summary: dict[str, dict[str, object]] = {}
    for benchmark, items in grouped.items():
        latencies = [float(item.latency_seconds) for item in items]
        summary[benchmark] = {
            "total": len(items),
            "passed": sum(1 for item in items if item.success),
            "failed": sum(1 for item in items if not item.success),
            "avg_latency_seconds": _safe_mean(latencies),
            "avg_quality_score": _safe_mean([item.quality_score for item in items]),
            "avg_speed_score": _safe_mean([item.speed_score for item in items]),
            "avg_cost_score": _safe_mean([item.cost_score for item in items]),
            "avg_streaming_score": _safe_mean([item.streaming_score for item in items]),
            "avg_multimodal_score": _safe_mean([item.multimodal_score for item in items]),
        }
    return summary


def _collect_failures(results: list[TaskResult]) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    for result in results:
        if result.success:
            continue
        failures.append(
            {
                "task_id": result.task_id,
                "benchmark": result.benchmark,
                "task_type": result.task_type.value,
                "latency_seconds": float(result.latency_seconds),
                "error": result.error or "unknown_error",
            }
        )
    return failures


def _collect_slow_tasks(results: list[TaskResult]) -> list[dict[str, object]]:
    latencies = _collect_latency(results)
    median = _percentile(latencies, 0.5)
    if median <= 0:
        return []
    threshold = median * 2
    slow: list[dict[str, object]] = []
    for result in results:
        if result.latency_seconds <= threshold:
            continue
        slow.append(
            {
                "task_id": result.task_id,
                "benchmark": result.benchmark,
                "task_type": result.task_type.value,
                "latency_seconds": float(result.latency_seconds),
                "threshold_seconds": threshold,
            }
        )
    return slow


def analyze_benchmark_results(report_path: str) -> PerformanceMetrics:
    """Analyze a benchmark report and extract performance metrics."""
    report = _load_report(report_path)
    results = list(report.results)

    ttft_ms = _collect_ttft_ms(results)
    tps_values = _collect_tps(results)
    latencies = _collect_latency(results)
    continuity_scores, continuity_gap_count = _collect_continuity(results)

    total_tokens = sum(result.total_tokens or 0 for result in results)
    total_cost = sum(result.cost_usd or 0.0 for result in results)
    total_tasks = len(results)

    return PerformanceMetrics(
        composite_score=report.composite_score,
        quality_score=report.quality_score,
        speed_score=report.speed_score,
        cost_score=report.cost_score,
        streaming_score=report.streaming_score,
        multimodal_score=report.multimodal_score,
        avg_ttft_ms=_safe_mean(ttft_ms),
        p50_ttft_ms=_percentile(ttft_ms, 0.5),
        p95_ttft_ms=_percentile(ttft_ms, 0.95),
        avg_tps=_safe_mean(tps_values),
        p50_tps=_percentile(tps_values, 0.5),
        p95_tps=_percentile(tps_values, 0.95),
        avg_latency_seconds=_safe_mean(latencies),
        p50_latency_seconds=_percentile(latencies, 0.5),
        p95_latency_seconds=_percentile(latencies, 0.95),
        continuity_score=_safe_mean(continuity_scores),
        continuity_gap_count=continuity_gap_count,
        total_tokens=total_tokens,
        avg_tokens_per_task=(total_tokens / total_tasks) if total_tasks else 0.0,
        total_cost_usd=total_cost,
        avg_cost_per_task=(total_cost / total_tasks) if total_tasks else 0.0,
        tasks_by_benchmark=_group_by_benchmark(results),
        failed_tasks=_collect_failures(results),
        slow_tasks=_collect_slow_tasks(results),
    )


def compare_baselines(cli_report: str, langchain_report: str) -> dict[str, Any]:
    """Compare performance between the two baselines."""
    cli_metrics = analyze_benchmark_results(cli_report)
    langchain_metrics = analyze_benchmark_results(langchain_report)

    def winner(cli_value: float, langchain_value: float) -> str:
        return "cli" if cli_value > langchain_value else "langchain"

    return {
        "winner_by_category": {
            "composite": winner(cli_metrics.composite_score, langchain_metrics.composite_score),
            "quality": winner(cli_metrics.quality_score, langchain_metrics.quality_score),
            "speed": winner(cli_metrics.speed_score, langchain_metrics.speed_score),
            "cost": winner(cli_metrics.cost_score, langchain_metrics.cost_score),
            "streaming": winner(cli_metrics.streaming_score, langchain_metrics.streaming_score),
        },
        "deltas": {
            "composite": cli_metrics.composite_score - langchain_metrics.composite_score,
            "quality": cli_metrics.quality_score - langchain_metrics.quality_score,
            "speed": cli_metrics.speed_score - langchain_metrics.speed_score,
            "cost": cli_metrics.cost_score - langchain_metrics.cost_score,
            "streaming": cli_metrics.streaming_score - langchain_metrics.streaming_score,
        },
        "cli_metrics": cli_metrics,
        "langchain_metrics": langchain_metrics,
    }
