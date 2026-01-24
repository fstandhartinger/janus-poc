"""Helpers for streaming benchmark metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TTFTMetric:
    """Time to first token summary."""

    value_ms: int
    percentile_90: int
    percentile_95: int
    percentile_99: int


@dataclass(frozen=True)
class TPSMetric:
    """Tokens per second metrics for a stream."""

    avg_tps: float
    peak_tps: float
    min_tps: float
    total_tokens: int
    total_time_ms: int


@dataclass(frozen=True)
class ContinuityMetric:
    """Continuity metrics for streaming smoothness."""

    score: float
    gap_count: int
    max_gap_ms: int
    coefficient_of_variation: float


def calculate_ttft(start_time: float, first_token_time: float) -> int:
    """Calculate time-to-first-token in milliseconds."""
    return int((first_token_time - start_time) * 1000)


def calculate_tps(tokens: Sequence[str], timestamps: Sequence[float]) -> TPSMetric:
    """Calculate TPS metrics from streamed token timestamps."""
    if len(tokens) < 2 or len(timestamps) < 2:
        return TPSMetric(0.0, 0.0, 0.0, len(tokens), 0)

    total_time = timestamps[-1] - timestamps[0]
    avg_tps = len(tokens) / total_time if total_time > 0 else 0.0

    window_rates: list[float] = []
    for i in range(len(timestamps) - 1):
        delta = timestamps[i + 1] - timestamps[i]
        if delta > 0:
            window_rates.append(1 / delta)

    return TPSMetric(
        avg_tps=avg_tps,
        peak_tps=max(window_rates) if window_rates else 0.0,
        min_tps=min(window_rates) if window_rates else 0.0,
        total_tokens=len(tokens),
        total_time_ms=int(total_time * 1000),
    )


def calculate_continuity(timestamps: Sequence[float]) -> ContinuityMetric:
    """Calculate continuity metrics based on inter-token timing variance."""
    if len(timestamps) < 3:
        return ContinuityMetric(1.0, 0, 0, 0.0)

    deltas_ms = [
        (timestamps[i + 1] - timestamps[i]) * 1000
        for i in range(len(timestamps) - 1)
    ]

    mean_delta = sum(deltas_ms) / len(deltas_ms)
    variance = sum((delta - mean_delta) ** 2 for delta in deltas_ms) / len(deltas_ms)
    std_dev = variance ** 0.5
    cv = std_dev / mean_delta if mean_delta > 0 else 0.0

    gap_threshold = mean_delta * 3
    gaps = [delta for delta in deltas_ms if delta > gap_threshold]

    cv_score = 1 / (1 + cv)
    gap_penalty = max(0.0, 1 - (len(gaps) * 0.1))
    score = cv_score * gap_penalty

    return ContinuityMetric(
        score=min(1.0, max(0.0, score)),
        gap_count=len(gaps),
        max_gap_ms=int(max(deltas_ms)) if deltas_ms else 0,
        coefficient_of_variation=cv,
    )
