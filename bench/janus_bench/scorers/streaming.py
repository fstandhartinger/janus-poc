"""Streaming continuity scoring for benchmark responses."""

from typing import Optional

from ..models import StreamingMetrics


def score_streaming(
    metrics: Optional[StreamingMetrics],
    max_allowed_gap: float = 2.0,
    target_ttft: float = 2.0,
) -> float:
    """Score streaming continuity based on gaps and TTFT.

    Args:
        metrics: Streaming metrics from the response
        max_allowed_gap: Maximum allowed gap between events (default 2s)
        target_ttft: Target time to first token (default 2s)

    Returns:
        Score between 0.0 and 1.0
    """
    if metrics is None:
        return 0.0

    # Score TTFT (50% of streaming score)
    if metrics.ttft_seconds <= target_ttft:
        ttft_score = 1.0
    elif metrics.ttft_seconds <= target_ttft * 2:
        ttft_score = 1.0 - 0.5 * ((metrics.ttft_seconds - target_ttft) / target_ttft)
    else:
        ttft_score = max(0.0, 0.5 - 0.2 * ((metrics.ttft_seconds - 2 * target_ttft) / target_ttft))

    # Score max gap (40% of streaming score)
    if metrics.max_gap_seconds <= max_allowed_gap:
        gap_score = 1.0
    elif metrics.max_gap_seconds <= max_allowed_gap * 2:
        gap_score = 1.0 - 0.5 * ((metrics.max_gap_seconds - max_allowed_gap) / max_allowed_gap)
    else:
        gap_score = max(0.0, 0.5 - 0.2 * ((metrics.max_gap_seconds - 2 * max_allowed_gap) / max_allowed_gap))

    # Score chunk count (10% - more chunks = better streaming)
    # Expect at least 5 chunks for a reasonable response
    if metrics.total_chunks >= 10:
        chunk_score = 1.0
    elif metrics.total_chunks >= 5:
        chunk_score = 0.8
    elif metrics.total_chunks >= 2:
        chunk_score = 0.5
    else:
        chunk_score = 0.2

    return 0.5 * ttft_score + 0.4 * gap_score + 0.1 * chunk_score
