"""Text evaluator for public benchmark tasks."""

from __future__ import annotations

from typing import Any

from .base import EvaluationResult


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _score_contains(response_text: str, items: list[str]) -> float:
    if not response_text or not items:
        return 0.0
    response_lower = response_text.lower()
    found = sum(1 for item in items if item.lower() in response_lower)
    return found / len(items)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def evaluate_text(
    response_text: str | None,
    expected: dict[str, Any],
    latency_seconds: float | None = None,
) -> EvaluationResult:
    """Evaluate a text response against expected constraints."""
    response_text = response_text or ""
    if not response_text.strip():
        return EvaluationResult(score=0.0, details={"reason": "empty_response"})

    components: dict[str, float] = {}

    contains = _as_list(expected.get("contains"))
    must_cover = _as_list(expected.get("must_cover"))

    if contains:
        components["contains"] = _score_contains(response_text, contains)
    if must_cover:
        components["must_cover"] = _score_contains(response_text, must_cover)

    min_length = expected.get("min_length")
    if isinstance(min_length, (int, float)) and min_length > 0:
        components["min_length"] = min(1.0, len(response_text) / float(min_length))

    max_latency_ms = expected.get("max_latency_ms")
    if (
        isinstance(max_latency_ms, (int, float))
        and max_latency_ms > 0
        and latency_seconds is not None
    ):
        latency_ms = latency_seconds * 1000.0
        components["latency"] = min(1.0, float(max_latency_ms) / latency_ms)

    score = _average(list(components.values())) if components else 1.0

    return EvaluationResult(score=score, details={"components": components})
