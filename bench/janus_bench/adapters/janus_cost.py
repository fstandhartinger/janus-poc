"""Adapter for Janus cost benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_COST)
class JanusCostAdapter(BenchmarkAdapter):
    """Benchmark for cost efficiency metrics."""

    name = BenchmarkName.JANUS_COST
    display_name = "Janus Cost"
    description = "Token and cost efficiency across tasks"
    data_file = "cost_items.json"
    task_type = TaskType.COST
