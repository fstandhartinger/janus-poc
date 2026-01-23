"""Benchmark definitions and Janus scoring categories."""

from __future__ import annotations

from .adapters import list_adapters
from .adapters.base import BenchmarkMetadata


JANUS_CATEGORY = "Janus Intelligence"
CORE_CATEGORY = "Core Benchmarks"
CORE_BENCHMARK = "core"


JANUS_SCORING_CATEGORIES = {
    "quality": {
        "weight": 0.40,
        "benchmarks": ("janus_research", "janus_tool_use"),
        "description": "Overall response quality and correctness",
    },
    "speed": {
        "weight": 0.20,
        "benchmarks": ("janus_streaming",),
        "metrics": ("ttft", "tps"),
    },
    "cost": {
        "weight": 0.15,
        "benchmarks": ("janus_cost",),
        "metrics": ("tokens_per_task", "cost_per_task"),
    },
    "streaming": {
        "weight": 0.15,
        "benchmarks": ("janus_streaming",),
        "metrics": ("continuity_score", "chunk_regularity"),
    },
    "modality": {
        "weight": 0.10,
        "benchmarks": ("janus_multimodal",),
        "description": "Image, audio, and multimodal handling",
    },
}


def get_janus_benchmarks() -> tuple[BenchmarkMetadata, ...]:
    """Return Janus benchmark metadata."""
    return tuple(adapter.get_metadata() for adapter in list_adapters())


def get_janus_benchmark_names() -> tuple[str, ...]:
    """Return Janus benchmark names in order."""
    return tuple(metadata.name for metadata in get_janus_benchmarks())
