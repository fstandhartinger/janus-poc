"""Cost efficiency scoring helpers for Janus cost benchmark."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class TokenMetrics:
    """Token usage for a single task."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int


@dataclass(frozen=True)
class CostMetrics:
    """Cost metrics for evaluation."""

    avg_input_tokens: float
    avg_output_tokens: float
    avg_total_tokens: float
    token_efficiency_score: float
    conciseness_score: float


def _estimate_tokens(text: str) -> int:
    words = text.split()
    return len(words)


def _length_score(word_count: int, max_words: int) -> float:
    if max_words <= 0:
        return 1.0
    if word_count <= max_words:
        return 1.0
    if word_count <= max_words * 2:
        return 0.5
    return 0.2


def calculate_cost_efficiency(
    quality_score: float,
    total_tokens: int,
    baseline_tokens: int,
) -> float:
    """Calculate cost efficiency score (0-1)."""
    if total_tokens <= 0 or baseline_tokens <= 0:
        return 0.0
    token_ratio = baseline_tokens / total_tokens
    token_ratio = min(2.0, token_ratio)
    efficiency = quality_score * (token_ratio / 2)
    return min(1.0, efficiency)


def evaluate_concise_response(
    response: str,
    required: list[str],
    max_words: int,
) -> tuple[float, str]:
    """Evaluate concise response quality."""
    response_lower = response.lower()
    found = sum(1 for req in required if req.lower() in response_lower)
    content_score = found / len(required) if required else 1.0

    word_count = len(response.split())
    length_score = _length_score(word_count, max_words)

    score = (content_score * 0.7) + (length_score * 0.3)
    return score, f"Content: {content_score:.2f}, Length: {word_count} words"


def evaluate_quality_and_tokens(
    response: str,
    output_tokens: int,
    quality_criteria: list[str],
    min_matches: int,
    baseline_tokens: int,
    max_tokens: int,
) -> tuple[float, str]:
    """Balance quality vs token usage."""
    response_lower = response.lower()
    required_matches = max(1, min_matches)
    matches = sum(1 for crit in quality_criteria if crit.lower() in response_lower)
    if matches >= required_matches:
        quality_score = matches / required_matches
    else:
        quality_score = (matches / required_matches) * 0.7

    if output_tokens <= baseline_tokens:
        token_score = 1.0
    elif output_tokens <= max_tokens:
        overage = output_tokens - baseline_tokens
        allowed_overage = max(1, max_tokens - baseline_tokens)
        token_score = 1.0 - (overage / allowed_overage * 0.5)
    else:
        token_score = 0.3

    score = (quality_score * 0.6) + (token_score * 0.4)
    return score, f"Quality: {quality_score:.2f}, Tokens: {output_tokens}/{baseline_tokens}"


def evaluate_tool_efficiency(
    response: str,
    tool_calls: list[str],
    evaluation: dict[str, Any],
) -> tuple[float, str]:
    """Evaluate minimal tool usage."""
    max_calls = int(evaluation.get("max_tool_calls", 1))
    expected = list(evaluation.get("expected_answer_contains") or [])

    response_lower = response.lower()
    correct = any(exp.lower() in response_lower for exp in expected)
    efficient = len(tool_calls) <= max_calls

    if correct and efficient:
        return 1.0, f"Correct with {len(tool_calls)} tool calls"
    if correct:
        return 0.6, f"Correct but used {len(tool_calls)} calls (max: {max_calls})"
    if efficient:
        return 0.3, "Efficient but incorrect"
    return 0.1, f"Incorrect and used {len(tool_calls)} calls"


def evaluate_directness(
    response: str,
    evaluation: dict[str, Any],
) -> tuple[float, str]:
    """Evaluate answer directness (answer appears early)."""
    answer_within = int(evaluation.get("answer_must_appear_within_first", 50))
    words = response.split()
    first_words = " ".join(words[:answer_within])
    numbers = re.findall(r"\d+\.?\d*", first_words)
    if numbers:
        return 1.0, f"Answer appears within first {answer_within} words"

    all_numbers = re.findall(r"\d+\.?\d*", response)
    if all_numbers:
        return 0.5, "Answer present but not direct"

    return 0.2, "Answer unclear or missing"


def score_cost_task(
    response_text: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    tool_calls: list[dict[str, Any]] | None,
    metadata: dict[str, Any] | None,
    reasoning_content: str | None = None,
) -> tuple[float, float, dict[str, Any]]:
    """Score a cost benchmark task and return quality/efficiency details."""
    response_text = response_text or ""
    metadata = metadata or {}
    evaluation = metadata.get("evaluation") or {}
    task_type = (
        metadata.get("cost_task_type")
        or metadata.get("task_type")
        or "cost"
    )

    tool_call_names: list[str] = []
    for call in tool_calls or []:
        name = call.get("function")
        if isinstance(name, str):
            tool_call_names.append(name)

    resolved_output_tokens = completion_tokens
    if resolved_output_tokens is None:
        resolved_output_tokens = _estimate_tokens(response_text)
    resolved_prompt_tokens = prompt_tokens or 0
    resolved_total_tokens = total_tokens
    if resolved_total_tokens is None:
        resolved_total_tokens = resolved_prompt_tokens + resolved_output_tokens
    if resolved_total_tokens <= 0:
        resolved_total_tokens = resolved_output_tokens

    reasoning_tokens = 0
    if reasoning_content:
        reasoning_tokens = _estimate_tokens(reasoning_content)

    if task_type == "concise_response":
        score, reasoning = evaluate_concise_response(
            response_text,
            list(evaluation.get("required") or []),
            int(evaluation.get("max_words", 50)),
        )
        word_count = len(response_text.split())
        conciseness_score = _length_score(word_count, int(evaluation.get("max_words", 50)))
    elif task_type == "efficient_explanation":
        score, reasoning = evaluate_quality_and_tokens(
            response_text,
            resolved_output_tokens,
            list(evaluation.get("quality_criteria") or []),
            int(evaluation.get("min_matches", 1)),
            int(evaluation.get("baseline_tokens", 100)),
            int(evaluation.get("max_tokens", 200)),
        )
        conciseness_score = None
    elif task_type == "minimal_tools":
        score, reasoning = evaluate_tool_efficiency(
            response_text,
            tool_call_names,
            evaluation,
        )
        conciseness_score = None
    elif task_type == "direct_answer":
        score, reasoning = evaluate_directness(response_text, evaluation)
        conciseness_score = None
    else:
        score, reasoning = 0.5, f"Unknown task type: {task_type}"
        conciseness_score = None

    baseline = int(evaluation.get("baseline_tokens", 0))
    if baseline <= 0:
        baseline = max(1, resolved_total_tokens)

    efficiency = calculate_cost_efficiency(score, resolved_total_tokens, baseline)

    details: dict[str, Any] = {
        "reasoning": reasoning,
        "quality_score": score,
        "efficiency_score": efficiency,
        "input_tokens": resolved_prompt_tokens,
        "output_tokens": resolved_output_tokens,
        "total_tokens": resolved_total_tokens,
        "baseline_tokens": baseline,
        "tool_calls": tool_call_names,
        "task_type": task_type,
        "reasoning_tokens": reasoning_tokens,
    }
    if conciseness_score is not None:
        details["conciseness_score"] = conciseness_score

    return score, efficiency, details
