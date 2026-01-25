"""Tests for janus-bench configuration."""

import pytest

from janus_bench.config import Settings


def test_weight_sum_validation() -> None:
    """Weights must sum to 100."""
    with pytest.raises(ValueError):
        Settings(
            weight_quality=30,
            weight_speed=20,
            weight_cost=15,
            weight_streaming=15,
            weight_multimodal=10,
        )


def test_weight_sum_valid() -> None:
    """Valid weight totals should be accepted."""
    settings = Settings(
        weight_quality=40,
        weight_speed=20,
        weight_cost=15,
        weight_streaming=15,
        weight_multimodal=10,
    )
    assert settings.weight_quality == 40
