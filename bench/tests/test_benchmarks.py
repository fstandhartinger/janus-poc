"""Tests for Janus benchmark metadata."""

from janus_bench.benchmarks import get_janus_benchmarks, get_janus_benchmark_names


def test_janus_benchmark_metadata():
    """Ensure Janus benchmark metadata is available and complete."""
    benchmarks = get_janus_benchmarks()
    expected_counts = {
        "janus_research": 100,
        "janus_tool_use": 80,
        "janus_multimodal": 60,
        "janus_streaming": 50,
        "janus_cost": 40,
    }

    assert len(benchmarks) == len(expected_counts)

    for benchmark in benchmarks:
        assert benchmark.name in expected_counts
        assert benchmark.category == "Janus Intelligence"
        assert benchmark.total_items == expected_counts[benchmark.name]
        assert benchmark.description


def test_janus_benchmark_names():
    """Ensure benchmark names list is stable."""
    names = get_janus_benchmark_names()
    assert set(names) == {
        "janus_research",
        "janus_tool_use",
        "janus_multimodal",
        "janus_streaming",
        "janus_cost",
    }
