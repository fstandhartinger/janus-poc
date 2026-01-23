"""Adapter for Janus streaming benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_STREAMING)
class JanusStreamingAdapter(BenchmarkAdapter):
    """Benchmark for streaming quality metrics."""

    name = BenchmarkName.JANUS_STREAMING
    display_name = "Janus Streaming"
    description = "Streaming quality metrics including TTFT and continuity"
    data_file = "streaming_items.json"
    task_type = TaskType.STREAMING
