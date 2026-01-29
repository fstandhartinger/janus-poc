"""Multimodal evaluator for public benchmark tasks."""

from __future__ import annotations

from typing import Any

from .base import EvaluationResult
from .text_evaluator import evaluate_text


def evaluate_multimodal(
    response_text: str | None,
    expected: dict[str, Any],
    has_image_input: bool,
    latency_seconds: float | None = None,
) -> EvaluationResult:
    result = evaluate_text(response_text, expected, latency_seconds)
    details = dict(result.details)
    details["has_image_input"] = has_image_input
    return EvaluationResult(score=result.score, details=details, reasoning=result.reasoning)
