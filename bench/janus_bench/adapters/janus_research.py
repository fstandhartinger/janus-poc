"""Adapter for Janus research benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_RESEARCH)
class JanusResearchAdapter(BenchmarkAdapter):
    """Benchmark for web research and synthesis capabilities."""

    name = BenchmarkName.JANUS_RESEARCH
    display_name = "Janus Research"
    description = "Web research, search, and synthesis capabilities"
    data_file = "research_items.json"
    task_type = TaskType.RESEARCH
