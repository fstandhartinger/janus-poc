"""Adapter for Janus tool-use benchmark."""

from ..models import BenchmarkName, TaskType
from .base import BenchmarkAdapter
from .registry import register_adapter


@register_adapter(BenchmarkName.JANUS_TOOL_USE)
class JanusToolUseAdapter(BenchmarkAdapter):
    """Benchmark for tool usage and API integration."""

    name = BenchmarkName.JANUS_TOOL_USE
    display_name = "Janus Tool Use"
    description = "Function calling and tool integration capabilities"
    data_file = "tool_use_items.json"
    task_type = TaskType.TOOL_USE
    subtask_metadata_key = "tool_use_task_type"
