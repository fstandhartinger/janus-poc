"""Speed scoring for benchmark responses."""


def score_speed(
    latency_seconds: float,
    ttft_seconds: float | None = None,
    tps: float | None = None,
    target_latency: float = 8.0,
    target_ttft: float = 2.0,
    target_tps: float = 10.0,
) -> float:
    """Score response speed based on latency and TTFT.

    Args:
        latency_seconds: Total response latency in seconds
        ttft_seconds: Time to first token in seconds (optional)
        tps: Tokens per second (optional)
        target_latency: Target P50 latency for full score (default 8s)
        target_ttft: Target TTFT for full score (default 2s)
        target_tps: Target tokens per second for full score (default 10)

    Returns:
        Score between 0.0 and 1.0
    """
    # Score latency for fallback
    if latency_seconds <= target_latency:
        latency_score = 1.0
    elif latency_seconds <= target_latency * 2:
        latency_score = 1.0 - 0.5 * ((latency_seconds - target_latency) / target_latency)
    else:
        latency_score = max(0.0, 0.5 - 0.1 * ((latency_seconds - 2 * target_latency) / target_latency))

    # Score TTFT
    if ttft_seconds is None:
        ttft_score = None
    else:
        if ttft_seconds <= target_ttft:
            ttft_score = 1.0
        elif ttft_seconds <= target_ttft * 2:
            ttft_score = 1.0 - 0.5 * ((ttft_seconds - target_ttft) / target_ttft)
        else:
            ttft_score = max(0.0, 0.5 - 0.1 * ((ttft_seconds - 2 * target_ttft) / target_ttft))

    # Score TPS
    if tps is None:
        tps_score = None
    else:
        if tps <= 0:
            tps_score = 0.0
        elif tps >= target_tps:
            tps_score = 1.0
        else:
            tps_score = max(0.0, tps / target_tps)

    # Combine scores with fallbacks
    if ttft_score is None and tps_score is None:
        return latency_score
    if ttft_score is None:
        assert tps_score is not None
        return tps_score
    if tps_score is None:
        assert ttft_score is not None
        return ttft_score
    return 0.5 * ttft_score + 0.5 * tps_score
