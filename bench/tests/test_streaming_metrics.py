"""Tests for streaming metric helpers."""

from janus_bench.streaming_metrics import (
    calculate_continuity,
    calculate_tps,
    calculate_ttft,
)


def test_calculate_ttft():
    """TTFT should return milliseconds."""
    assert calculate_ttft(1.0, 1.25) == 250


def test_calculate_tps_basic():
    """TPS metrics should reflect token timing."""
    tokens = ["a", "b", "c"]
    timestamps = [0.0, 0.5, 1.0]
    metrics = calculate_tps(tokens, timestamps)

    assert metrics.total_tokens == 3
    assert metrics.total_time_ms == 1000
    assert metrics.avg_tps == 3.0
    assert metrics.peak_tps == 2.0
    assert metrics.min_tps == 2.0


def test_calculate_tps_single_token():
    """Single-token streams should yield zero rates."""
    metrics = calculate_tps(["a"], [0.0])

    assert metrics.total_tokens == 1
    assert metrics.total_time_ms == 0
    assert metrics.avg_tps == 0.0


def test_calculate_continuity_perfect():
    """Even spacing should yield perfect continuity."""
    timestamps = [0.0, 0.5, 1.0, 1.5]
    metrics = calculate_continuity(timestamps)

    assert metrics.score == 1.0
    assert metrics.gap_count == 0
    assert metrics.max_gap_ms == 500


def test_calculate_continuity_with_gap():
    """Large gaps should reduce the continuity score."""
    timestamps = [0.0, 0.1, 0.2, 0.3, 3.3]
    metrics = calculate_continuity(timestamps)

    assert metrics.gap_count >= 1
    assert 0.0 <= metrics.score < 1.0
