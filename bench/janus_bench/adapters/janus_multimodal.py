"""Adapter for Janus multimodal benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_MULTIMODAL)
class JanusMultimodalAdapter(BenchmarkAdapter):
    """Benchmark for multimodal handling."""

    name = BenchmarkName.JANUS_MULTIMODAL
    display_name = "Janus Multimodal"
    description = "Image generation and vision handling capabilities"
    data_file = "multimodal_items.json"
    task_type = TaskType.MULTIMODAL
