"""Cost scoring for benchmark responses."""


def score_cost(
    total_tokens: int | None = None,
    cost_usd: float | None = None,
    sandbox_seconds: float | None = None,
    target_tokens: int = 1000,
    target_cost: float = 0.01,
    target_sandbox_seconds: float = 30.0,
) -> float:
    """Score response cost based on tokens, USD cost, and sandbox usage.

    Args:
        total_tokens: Total tokens used
        cost_usd: Cost in USD (optional)
        sandbox_seconds: Sandbox execution time (optional)
        target_tokens: Target token count for full score
        target_cost: Target cost in USD for full score
        target_sandbox_seconds: Target sandbox time for full score

    Returns:
        Score between 0.0 and 1.0
    """
    scores = []
    weights = []

    # Score token usage (if available)
    if total_tokens is not None:
        if total_tokens <= target_tokens:
            token_score = 1.0
        elif total_tokens <= target_tokens * 2:
            token_score = 1.0 - 0.5 * ((total_tokens - target_tokens) / target_tokens)
        else:
            token_score = max(0.0, 0.5 - 0.1 * ((total_tokens - 2 * target_tokens) / target_tokens))
        scores.append(token_score)
        weights.append(0.5)

    # Score USD cost (if available)
    if cost_usd is not None:
        if cost_usd <= target_cost:
            cost_score = 1.0
        elif cost_usd <= target_cost * 2:
            cost_score = 1.0 - 0.5 * ((cost_usd - target_cost) / target_cost)
        else:
            cost_score = max(0.0, 0.5 - 0.1 * ((cost_usd - 2 * target_cost) / target_cost))
        scores.append(cost_score)
        weights.append(0.3)

    # Score sandbox usage (if available)
    if sandbox_seconds is not None:
        if sandbox_seconds <= target_sandbox_seconds:
            sandbox_score = 1.0
        elif sandbox_seconds <= target_sandbox_seconds * 2:
            sandbox_score = 1.0 - 0.5 * ((sandbox_seconds - target_sandbox_seconds) / target_sandbox_seconds)
        else:
            sandbox_score = max(0.0, 0.5 - 0.1 * ((sandbox_seconds - 2 * target_sandbox_seconds) / target_sandbox_seconds))
        scores.append(sandbox_score)
        weights.append(0.2)

    # If no cost data available, return default neutral score
    if not scores:
        return 0.5

    # Weighted average
    total_weight = sum(weights)
    return sum(s * w for s, w in zip(scores, weights)) / total_weight
