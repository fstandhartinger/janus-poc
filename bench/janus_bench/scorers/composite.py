"""Composite score calculation."""

from typing import Optional

from ..models import TaskResult, StreamingMetrics, TaskType
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
) -> TaskResult:
    """Compute all component scores for a task result.

    Args:
        result: Task result to score
        expected_answer: Optional expected answer for quality scoring
        expected_keywords: Optional expected keywords for quality scoring
        has_image_input: Whether the task had image input

    Returns:
        Updated TaskResult with scores filled in
    """
    # Quality score
    result.quality_score = score_quality(
        result.response_text,
        expected_answer,
        expected_keywords,
    )

    # Speed score
    ttft = result.streaming_metrics.ttft_seconds if result.streaming_metrics else None
    result.speed_score = score_speed(result.latency_seconds, ttft)

    # Cost score
    result.cost_score = score_cost(
        result.total_tokens,
        result.cost_usd,
        result.sandbox_seconds,
    )

    # Streaming score
    result.streaming_score = score_streaming(result.streaming_metrics)

    # Multimodal score
    result.multimodal_score = score_multimodal(
        result.response_text,
        has_image_input,
        expected_keywords,
    )

    return result


def compute_composite_score(
    results: list[TaskResult],
    weight_quality: int = 45,
    weight_speed: int = 20,
    weight_cost: int = 15,
    weight_streaming: int = 10,
    weight_multimodal: int = 10,
) -> dict[str, float]:
    """Compute composite and component scores from task results.

    Args:
        results: List of task results with individual scores
        weight_quality: Quality weight (default 45%)
        weight_speed: Speed weight (default 20%)
        weight_cost: Cost weight (default 15%)
        weight_streaming: Streaming weight (default 10%)
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
        }

    # Average each component score
    n = len(results)
    avg_quality = sum(r.quality_score for r in results) / n
    avg_speed = sum(r.speed_score for r in results) / n
    avg_cost = sum(r.cost_score for r in results) / n
    avg_streaming = sum(r.streaming_score for r in results) / n

    # For multimodal, only average multimodal tasks
    multimodal_results = [r for r in results if r.task_type == TaskType.MULTIMODAL]
    if multimodal_results:
        avg_multimodal = sum(r.multimodal_score for r in multimodal_results) / len(multimodal_results)
    else:
        avg_multimodal = 1.0  # No multimodal tasks - full score

    # Compute weighted composite
    total_weight = weight_quality + weight_speed + weight_cost + weight_streaming + weight_multimodal
    composite = (
        weight_quality * avg_quality +
        weight_speed * avg_speed +
        weight_cost * avg_cost +
        weight_streaming * avg_streaming +
        weight_multimodal * avg_multimodal
    ) / total_weight

    # Return scores on 0-100 scale
    return {
        "composite_score": composite * 100,
        "quality_score": avg_quality * 100,
        "speed_score": avg_speed * 100,
        "cost_score": avg_cost * 100,
        "streaming_score": avg_streaming * 100,
        "multimodal_score": avg_multimodal * 100,
    }
