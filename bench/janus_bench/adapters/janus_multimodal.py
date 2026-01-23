"""Adapter for Janus multimodal benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_MULTIMODAL)
class JanusMultimodalAdapter(BenchmarkAdapter):
    """Benchmark for multimodal handling."""

    name = BenchmarkName.JANUS_MULTIMODAL
    display_name = "Janus Multimodal"
    description = "Image generation, vision understanding, and routing"
    data_file = "multimodal_items.json"
    task_type = TaskType.MULTIMODAL
    subtask_metadata_key = "multimodal_task_type"
