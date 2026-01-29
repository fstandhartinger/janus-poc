"""Citation-aware evaluator for research tasks."""

from __future__ import annotations

import re
from typing import Any

from ..scorers.research import detect_search_usage
from .base import EvaluationResult
from .text_evaluator import evaluate_text


URL_PATTERN = re.compile(r"https?://[^\s\)\]]+")
BRACKET_PATTERN = re.compile(r"\[(\d+)\]")


def _count_citations(response_text: str) -> int:
    urls = URL_PATTERN.findall(response_text)
    brackets = BRACKET_PATTERN.findall(response_text)
    return len(urls) + len(brackets)


def evaluate_citations(
    response_text: str | None,
    expected: dict[str, Any],
    latency_seconds: float | None = None,
) -> EvaluationResult:
    base_result = evaluate_text(response_text, expected, latency_seconds)
    response_text = response_text or ""

    components = dict(base_result.details.get("components", {}))

    requires_citations = bool(expected.get("requires_citations"))
    min_sources = expected.get("min_sources")
    if not isinstance(min_sources, (int, float)) or min_sources <= 0:
        min_sources = 1 if requires_citations else 0

    citation_count = _count_citations(response_text)
    if min_sources:
        components["citations"] = min(1.0, citation_count / float(min_sources))

    if requires_citations and citation_count == 0:
        components["citations"] = 0.0

    score = sum(components.values()) / len(components) if components else base_result.score

    details = {
        "components": components,
        "citation_count": citation_count,
        "search_used": detect_search_usage(response_text),
    }

    return EvaluationResult(score=score, details=details)
