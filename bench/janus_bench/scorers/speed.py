"""Speed scoring for benchmark responses."""


def score_speed(
    latency_seconds: float,
    ttft_seconds: float | None = None,
    target_latency: float = 8.0,
    target_ttft: float = 2.0,
) -> float:
    """Score response speed based on latency and TTFT.

    Args:
        latency_seconds: Total response latency in seconds
        ttft_seconds: Time to first token in seconds (optional)
        target_latency: Target P50 latency for full score (default 8s)
        target_ttft: Target TTFT for full score (default 2s)

    Returns:
        Score between 0.0 and 1.0
    """
    # Score latency (60% of speed score)
    if latency_seconds <= target_latency:
        latency_score = 1.0
    elif latency_seconds <= target_latency * 2:
        # Linear decay from 1.0 to 0.5 between target and 2x target
        latency_score = 1.0 - 0.5 * ((latency_seconds - target_latency) / target_latency)
    else:
        # Further decay for very slow responses
        latency_score = max(0.0, 0.5 - 0.1 * ((latency_seconds - 2 * target_latency) / target_latency))

    # Score TTFT (40% of speed score)
    if ttft_seconds is None:
        # No TTFT data - use latency score only
        return latency_score

    if ttft_seconds <= target_ttft:
        ttft_score = 1.0
    elif ttft_seconds <= target_ttft * 2:
        ttft_score = 1.0 - 0.5 * ((ttft_seconds - target_ttft) / target_ttft)
    else:
        ttft_score = max(0.0, 0.5 - 0.1 * ((ttft_seconds - 2 * target_ttft) / target_ttft))

    # Combine scores
    return 0.6 * latency_score + 0.4 * ttft_score
