"""Composite score calculation."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ..janus_scoring import calculate_janus_composite_score
from ..models import TaskResult
from .quality import score_quality
from .speed import score_speed
from .cost import score_cost
from .streaming import score_streaming
from .multimodal import score_multimodal


def compute_task_scores(
    result: TaskResult,
    expected_answer: Optional[str] = None,
    expected_keywords: Optional[list[str]] = None,
    has_image_input: bool = False,
    metadata: Optional[dict[str, Any]] = None,
    prompt: Optional[str] = None,
) -> TaskResult:
    """Compute all component scores for a task result.

    Args:
        result: Task result to score
        expected_answer: Optional expected answer for quality scoring
        expected_keywords: Optional expected keywords for quality scoring
        has_image_input: Whether the task had image input
        metadata: Optional metadata payload for task-specific scoring
        prompt: Optional prompt string for scoring context

    Returns:
        Updated TaskResult with scores filled in
    """
    # Quality score
    if result.judge_score is None and not (
        result.metadata and result.metadata.get("quality_override")
    ):
        result.quality_score = score_quality(
            result.response_text,
            expected_answer,
            expected_keywords,
        )

    # Speed score
    ttft = result.streaming_metrics.ttft_seconds if result.streaming_metrics else None
    tps = None
    if result.streaming_metrics and result.streaming_metrics.total_duration_seconds > 0:
        token_count = result.completion_tokens or result.total_tokens
        if token_count:
            tps = token_count / result.streaming_metrics.total_duration_seconds
        elif result.streaming_metrics.avg_tps is not None:
            tps = result.streaming_metrics.avg_tps
    result.tokens_per_second = tps
    result.speed_score = score_speed(result.latency_seconds, ttft, tps)

    # Cost score
    if not (result.metadata and result.metadata.get("cost_override")):
        result.cost_score = score_cost(
            result.total_tokens,
            result.cost_usd,
            result.sandbox_seconds,
        )

    # Streaming score
    result.streaming_score = score_streaming(result.streaming_metrics, metadata)

    # Multimodal score
    result.multimodal_score = score_multimodal(
        result.response_text,
        has_image_input,
        expected_keywords,
        metadata,
        prompt,
    )

    return result


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(len(ordered) * percentile)
    if index >= len(ordered):
        index = len(ordered) - 1
    return ordered[index]


def _build_benchmark_results(results: list[TaskResult]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[TaskResult]] = {}
    for result in results:
        if not result.benchmark:
            continue
        grouped.setdefault(result.benchmark, []).append(result)

    benchmark_results: dict[str, dict[str, Any]] = {}

    def add_benchmark(
        name: str,
        score_values: list[float],
        metrics: Mapping[str, object] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"score": _average(score_values)}
        if metrics:
            payload["metrics"] = dict(metrics)
        benchmark_results[name] = payload

    research_results = grouped.get("janus_research", [])
    tool_results = grouped.get("janus_tool_use", [])
    multimodal_results = grouped.get("janus_multimodal", [])
    streaming_results = grouped.get("janus_streaming", [])
    cost_results = grouped.get("janus_cost", [])

    if research_results:
        metrics: dict[str, object] = {}
        latencies_ms = [
            r.latency_seconds * 1000
            for r in research_results
            if r.latency_seconds is not None
        ]
        if latencies_ms:
            metrics["avg_latency_ms"] = _average(latencies_ms)

        task_type_scores: dict[str, list[float]] = {}
        search_count = 0
        citation_count = 0

        valid_results = [r for r in research_results if r.response_text and not r.error]
        for result in valid_results:
            task_type = "unknown"
            if result.metadata:
                task_type = result.metadata.get("research_task_type", task_type)
                if result.metadata.get("search_used"):
                    search_count += 1
                if result.metadata.get("citation_used"):
                    citation_count += 1
            task_type_scores.setdefault(task_type, []).append(result.quality_score)

        if valid_results:
            metrics["search_usage_rate"] = search_count / len(valid_results)
            metrics["citation_rate"] = citation_count / len(valid_results)

        if task_type_scores:
            metrics["by_task_type"] = {
                task_type: {
                    "count": len(scores),
                    "avg_score": _average(scores),
                }
                for task_type, scores in task_type_scores.items()
            }

        add_benchmark("janus_research", [r.quality_score for r in research_results], metrics)
    if tool_results:
        add_benchmark("janus_tool_use", [r.quality_score for r in tool_results])
    if multimodal_results:
        add_benchmark("janus_multimodal", [r.multimodal_score for r in multimodal_results])
    if streaming_results:
        ttft_values = [
            r.streaming_metrics.ttft_seconds * 1000
            for r in streaming_results
            if r.streaming_metrics
            and (not r.metadata or r.metadata.get("first_token_received", True))
        ]
        tps_values: list[float] = []
        continuity_values: list[float] = []
        streaming_scores = [r.streaming_score for r in streaming_results]
        for result in streaming_results:
            if result.streaming_metrics and result.streaming_metrics.avg_tps is not None:
                tps_values.append(result.streaming_metrics.avg_tps)
            elif result.tokens_per_second is not None:
                tps_values.append(result.tokens_per_second)
            if (
                result.streaming_metrics
                and result.streaming_metrics.continuity_score is not None
            ):
                continuity_values.append(result.streaming_metrics.continuity_score)
        chunk_regularities = [
            max(0.0, 1.0 - (r.streaming_metrics.max_gap_seconds / r.streaming_metrics.total_duration_seconds))
            for r in streaming_results
            if r.streaming_metrics and r.streaming_metrics.total_duration_seconds > 0
        ]
        streaming_metrics: dict[str, float] = {}
        if ttft_values:
            streaming_metrics["avg_ttft_ms"] = _average(ttft_values)
            p90 = _percentile(ttft_values, 0.90)
            p95 = _percentile(ttft_values, 0.95)
            p99 = _percentile(ttft_values, 0.99)
            if p90 is not None:
                streaming_metrics["p90_ttft_ms"] = p90
            if p95 is not None:
                streaming_metrics["p95_ttft_ms"] = p95
            if p99 is not None:
                streaming_metrics["p99_ttft_ms"] = p99
        if tps_values:
            streaming_metrics["avg_tps"] = _average(tps_values)
        if continuity_values:
            avg_continuity = _average(continuity_values)
            streaming_metrics["avg_continuity"] = avg_continuity
            streaming_metrics["continuity_score"] = avg_continuity
        if chunk_regularities:
            streaming_metrics["chunk_regularity"] = _average(chunk_regularities)
        streaming_metrics["samples"] = float(len(ttft_values))
        add_benchmark("janus_streaming", streaming_scores, streaming_metrics)
    if cost_results:
        token_values = [float(r.total_tokens) for r in cost_results if r.total_tokens is not None]
        cost_values = [r.cost_usd for r in cost_results if r.cost_usd is not None]
        cost_metrics: dict[str, float] = {}
        if token_values:
            cost_metrics["tokens_per_task"] = _average(token_values)
        if cost_values:
            cost_metrics["cost_per_task"] = _average(cost_values)
        valid_cost = [r for r in cost_results if r.judge_output]
        total_input = 0
        total_output = 0
        total_tokens = 0
        total_baseline = 0
        quality_scores: list[float] = []
        efficiency_scores: list[float] = []
        conciseness_scores: list[float] = []

        for result in valid_cost:
            output = result.judge_output or {}
            total_input += int(output.get("input_tokens", 0))
            total_output += int(output.get("output_tokens", 0))
            total_tokens += int(output.get("total_tokens", 0))
            total_baseline += int(output.get("baseline_tokens", 0))
            quality_scores.append(float(output.get("quality_score", 0.0)))
            efficiency_scores.append(float(output.get("efficiency_score", result.cost_score)))
            if "conciseness_score" in output:
                conciseness_scores.append(float(output.get("conciseness_score", 0.0)))

        n = len(valid_cost)
        if n:
            cost_metrics["avg_input_tokens"] = total_input / n
            cost_metrics["avg_output_tokens"] = total_output / n
            cost_metrics["avg_total_tokens"] = total_tokens / n
            cost_metrics["avg_quality_score"] = _average(quality_scores)
            cost_metrics["avg_efficiency_score"] = _average(efficiency_scores)
            if conciseness_scores:
                cost_metrics["avg_conciseness_score"] = _average(conciseness_scores)
            cost_metrics["baseline_tokens"] = total_baseline
            cost_metrics["samples"] = float(n)
            if total_baseline > 0:
                cost_metrics["token_savings_pct"] = (
                    (total_baseline - total_output) / total_baseline * 100
                )
        add_benchmark("janus_cost", [r.cost_score for r in cost_results], cost_metrics)

    return benchmark_results


def compute_composite_score(
    results: list[TaskResult],
    weight_quality: int = 40,
    weight_speed: int = 20,
    weight_cost: int = 15,
    weight_streaming: int = 15,
    weight_multimodal: int = 10,
) -> dict[str, object]:
    """Compute Janus composite and component scores from task results.

    Args:
        results: List of task results with individual scores
        weight_quality: Quality weight (default 40%)
        weight_speed: Speed weight (default 20%)
        weight_cost: Cost weight (default 15%)
        weight_streaming: Streaming weight (default 15%)
        weight_multimodal: Multimodal weight (default 10%)

    Returns:
        Dictionary with composite_score and component scores (all 0-100 scale)
    """
    if not results:
        return {
            "composite_score": 0.0,
            "quality_score": 0.0,
            "speed_score": 0.0,
            "cost_score": 0.0,
            "streaming_score": 0.0,
            "multimodal_score": 0.0,
            "benchmark_scores": {},
            "benchmark_metrics": {},
        }

    janus_results = [
        result for result in results if result.benchmark and result.benchmark.startswith("janus_")
    ]
    non_janus_results = [
        result
        for result in results
        if not result.benchmark or not result.benchmark.startswith("janus_")
    ]
    has_janus_only = bool(janus_results) and not non_janus_results

    if has_janus_only:
        benchmark_results = _build_benchmark_results(results)
        janus_scores = calculate_janus_composite_score(benchmark_results)

        composite = janus_scores["composite"] * 100
        quality = janus_scores["quality"] * 100
        speed = janus_scores["speed"] * 100
        cost = janus_scores["cost"] * 100
        streaming = janus_scores["streaming"] * 100
        multimodal = janus_scores["modality"] * 100

        benchmark_scores = {
            name: float(payload.get("score") or 0.0) * 100
            for name, payload in benchmark_results.items()
        }
        benchmark_metrics = {
            name: payload.get("metrics", {})
            for name, payload in benchmark_results.items()
            if payload.get("metrics")
        }
    else:
        avg_quality = _average([r.quality_score for r in results])
        avg_speed = _average([r.speed_score for r in results])
        avg_cost = _average([r.cost_score for r in results])
        avg_streaming = _average([r.streaming_score for r in results])

        multimodal_results = [r for r in results if r.task_type.value == "multimodal"]
        if multimodal_results:
            avg_multimodal = _average([r.multimodal_score for r in multimodal_results])
        else:
            avg_multimodal = 1.0

        total_weight = (
            weight_quality + weight_speed + weight_cost + weight_streaming + weight_multimodal
        )
        composite = (
            weight_quality * avg_quality
            + weight_speed * avg_speed
            + weight_cost * avg_cost
            + weight_streaming * avg_streaming
            + weight_multimodal * avg_multimodal
        ) / total_weight

        composite *= 100
        quality = avg_quality * 100
        speed = avg_speed * 100
        cost = avg_cost * 100
        streaming = avg_streaming * 100
        multimodal = avg_multimodal * 100
        benchmark_scores = {}
        benchmark_metrics = {}

    return {
        "composite_score": composite,
        "quality_score": quality,
        "speed_score": speed,
        "cost_score": cost,
        "streaming_score": streaming,
        "multimodal_score": multimodal,
        "benchmark_scores": benchmark_scores,
        "benchmark_metrics": benchmark_metrics,
    }
