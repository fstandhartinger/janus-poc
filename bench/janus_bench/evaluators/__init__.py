"""Public benchmark evaluators."""

from __future__ import annotations

from typing import Any

from ..models import BenchmarkTask, TaskResult, TaskType
from .base import EvaluationResult
from .citation_evaluator import evaluate_citations
from .code_evaluator import evaluate_code
from .multimodal_evaluator import evaluate_multimodal
from .text_evaluator import evaluate_text

__all__ = ["EvaluationResult", "evaluate_task_response"]


def _has_image_input(task: BenchmarkTask) -> bool:
    if task.image_url:
        return True
    metadata = task.metadata or {}
    messages = metadata.get("messages")
    if not isinstance(messages, list):
        return False
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                return True
    return False


def evaluate_task_response(
    task: BenchmarkTask,
    result: TaskResult,
) -> EvaluationResult | None:
    metadata = task.metadata or {}
    expected = metadata.get("expected")
    if not isinstance(expected, dict):
        return None

    expected_type = expected.get("type")
    latency = result.latency_seconds

    if task.type == TaskType.CODING or expected_type == "code":
        return evaluate_code(result.response_text, expected)

    if task.type == TaskType.MULTIMODAL or expected_type == "multimodal":
        return evaluate_multimodal(
            result.response_text,
            expected,
            has_image_input=_has_image_input(task),
            latency_seconds=latency,
        )

    if task.type == TaskType.RESEARCH and (
        expected.get("requires_citations") or expected.get("min_sources")
    ):
        return evaluate_citations(result.response_text, expected, latency_seconds=latency)

    return evaluate_text(result.response_text, expected, latency_seconds=latency)
