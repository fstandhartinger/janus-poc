"""Research benchmark scoring helpers."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable


SEARCH_INDICATORS = (
    "according to",
    "source:",
    "sources:",
    "search results",
    "reported by",
    "as reported by",
    "from the report",
)

CITATION_PATTERN = re.compile(r"https?://|www\.|\[[0-9]+\]|\(source\)", re.IGNORECASE)


def detect_search_usage(response_text: str | None) -> bool:
    if not response_text:
        return False
    response_lower = response_text.lower()
    return any(indicator in response_lower for indicator in SEARCH_INDICATORS)


def detect_citations(response_text: str | None) -> bool:
    if not response_text:
        return False
    return CITATION_PATTERN.search(response_text) is not None


def score_key_facts(response_text: str | None, expected_facts: Iterable[str]) -> float:
    if not response_text:
        return 0.0
    expected = [fact for fact in expected_facts if fact]
    if not expected:
        return 0.0
    response_lower = response_text.lower()
    found = sum(1 for fact in expected if fact.lower() in response_lower)
    return found / len(expected)


def build_judge_prompt(
    task_type: str,
    query: str,
    evaluation: dict[str, Any],
    response: str,
) -> str:
    evaluation_json = json.dumps(evaluation or {}, indent=2, sort_keys=True)
    return (
        "You are evaluating a research response.\n\n"
        f"Task Type: {task_type}\n"
        f"Query: {query}\n\n"
        "Response to evaluate:\n"
        f"{response}\n\n"
        "Evaluation criteria:\n"
        f"{evaluation_json}\n\n"
        "Score the response 0.0-1.0 and explain your reasoning.\n"
        'Output JSON with "score" and "reasoning" fields.'
    )


def parse_json_block(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def extract_judge_score(payload: dict[str, Any] | None) -> float | None:
    if not payload:
        return None

    if "score" in payload:
        return _clamp_score(payload.get("score"))

    if "overall_score" in payload:
        return _clamp_score(payload.get("overall_score"))

    score_fields = [
        payload.get("factual_accuracy"),
        payload.get("source_quality"),
        payload.get("completeness"),
        payload.get("synthesis"),
        payload.get("citation"),
    ]
    scores = [score for score in score_fields if isinstance(score, (int, float))]
    if scores:
        return _clamp_score(sum(scores) / len(scores))

    return None


def _clamp_score(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return max(0.0, min(1.0, float(value)))
