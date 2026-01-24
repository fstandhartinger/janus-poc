"""Streaming continuity scoring for benchmark responses."""

from typing import Any, Optional

from ..models import StreamingMetrics


def _score_streaming_with_targets(
    metrics: StreamingMetrics,
    evaluation: dict[str, Any],
    metadata: dict[str, Any],
) -> float:
    ttft_target = evaluation.get("ttft_target_ms", 1000)
    tps_target = evaluation.get("tps_target", 10)
    continuity_target = evaluation.get("continuity_target", 0.5)
    min_tokens = evaluation.get("min_tokens", 10)
    check_reasoning = evaluation.get("check_reasoning_content", False)

    first_token_received = metadata.get("first_token_received", True)
    ttft_ms = int(metrics.ttft_seconds * 1000) if first_token_received else None
    avg_tps = metrics.avg_tps or 0.0
    continuity_score = metrics.continuity_score or 0.0
    token_count = metrics.total_tokens or 0

    scores: list[tuple[float, float]] = []

    if ttft_ms is not None:
        if ttft_ms <= ttft_target:
            ttft_score = 1.0
        elif ttft_ms <= ttft_target * 2:
            ttft_score = 0.7
        elif ttft_ms <= ttft_target * 3:
            ttft_score = 0.4
        else:
            ttft_score = 0.1
    else:
        ttft_score = 0.0
    scores.append((ttft_score, 0.30))

    if tps_target <= 0:
        tps_score = 0.0
    elif avg_tps >= tps_target:
        tps_score = 1.0
    elif avg_tps >= tps_target * 0.5:
        tps_score = 0.7
    else:
        tps_score = max(0.1, avg_tps / tps_target)
    scores.append((tps_score, 0.30))

    if continuity_target <= 0:
        cont_score = 0.0
    elif continuity_score >= continuity_target:
        cont_score = 1.0
    else:
        cont_score = continuity_score / continuity_target
    scores.append((cont_score, 0.25))

    if min_tokens <= 0:
        completion_score = 1.0
    elif token_count >= min_tokens:
        completion_score = 1.0
    else:
        completion_score = token_count / min_tokens
    scores.append((completion_score, 0.15))

    task_type = metadata.get("task_type", "")
    has_reasoning = bool(metadata.get("has_reasoning_content"))
    if task_type == "reasoning_response" and check_reasoning and has_reasoning:
        scores.append((1.0, 0.05))

    total_weight = sum(weight for _, weight in scores)
    if total_weight <= 0:
        return 0.0
    return sum(score * weight for score, weight in scores) / total_weight


def _score_streaming_generic(
    metrics: StreamingMetrics,
    max_allowed_gap: float = 2.0,
    target_ttft: float = 2.0,
) -> float:
    if metrics.ttft_seconds <= target_ttft:
        ttft_score = 1.0
    elif metrics.ttft_seconds <= target_ttft * 2:
        ttft_score = 1.0 - 0.5 * ((metrics.ttft_seconds - target_ttft) / target_ttft)
    else:
        ttft_score = max(
            0.0,
            0.5 - 0.2 * ((metrics.ttft_seconds - 2 * target_ttft) / target_ttft),
        )

    if metrics.max_gap_seconds <= max_allowed_gap:
        gap_score = 1.0
    elif metrics.max_gap_seconds <= max_allowed_gap * 2:
        gap_score = 1.0 - 0.5 * (
            (metrics.max_gap_seconds - max_allowed_gap) / max_allowed_gap
        )
    else:
        gap_score = max(
            0.0,
            0.5 - 0.2 * ((metrics.max_gap_seconds - 2 * max_allowed_gap) / max_allowed_gap),
        )

    if metrics.total_chunks >= 10:
        chunk_score = 1.0
    elif metrics.total_chunks >= 5:
        chunk_score = 0.8
    elif metrics.total_chunks >= 2:
        chunk_score = 0.5
    else:
        chunk_score = 0.2

    return 0.5 * ttft_score + 0.4 * gap_score + 0.1 * chunk_score


def score_streaming(
    metrics: Optional[StreamingMetrics],
    metadata: Optional[dict[str, Any]] = None,
    max_allowed_gap: float = 2.0,
    target_ttft: float = 2.0,
) -> float:
    """Score streaming continuity based on gaps and TTFT."""
    if metrics is None:
        return 0.0

    evaluation: dict[str, Any] = {}
    if metadata:
        evaluation_candidate = metadata.get("evaluation")
        if isinstance(evaluation_candidate, dict):
            evaluation = evaluation_candidate

    if evaluation:
        return _score_streaming_with_targets(metrics, evaluation, metadata or {})

    return _score_streaming_generic(metrics, max_allowed_gap, target_ttft)
