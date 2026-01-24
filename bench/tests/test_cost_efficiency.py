"""Tests for cost efficiency scoring helpers."""

import pytest

from janus_bench.scorers.cost_efficiency import (
    calculate_cost_efficiency,
    evaluate_concise_response,
    evaluate_directness,
    evaluate_quality_and_tokens,
    evaluate_tool_efficiency,
    score_cost_task,
)


def test_calculate_cost_efficiency_caps_ratio():
    assert calculate_cost_efficiency(1.0, 50, 100) == pytest.approx(1.0)
    assert calculate_cost_efficiency(0.5, 100, 100) == pytest.approx(0.25)


def test_evaluate_concise_response_scores_content_and_length():
    score, reasoning = evaluate_concise_response(
        "World War II ended in 1945.",
        ["1945"],
        10,
    )
    assert score >= 0.9
    assert "Length" in reasoning


def test_evaluate_quality_and_tokens_balances_quality():
    score, _ = evaluate_quality_and_tokens(
        "An API is an interface that lets applications communicate.",
        80,
        ["interface", "communicate", "applications"],
        2,
        100,
        150,
    )
    assert score >= 0.8


def test_evaluate_tool_efficiency_penalizes_extra_calls():
    score, _ = evaluate_tool_efficiency(
        "The answer is 30.",
        ["calculator", "calculator"],
        {"max_tool_calls": 0, "expected_answer_contains": ["30"]},
    )
    assert score == pytest.approx(0.6)


def test_evaluate_directness_rewards_early_number():
    score, _ = evaluate_directness(
        "30 is the result.",
        {"answer_must_appear_within_first": 5},
    )
    assert score == pytest.approx(1.0)


def test_score_cost_task_builds_details():
    quality_score, efficiency_score, details = score_cost_task(
        response_text="Answer: 30.",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        tool_calls=[{"function": "calculator", "arguments": {}}],
        metadata={
            "cost_task_type": "minimal_tools",
            "evaluation": {
                "max_tool_calls": 1,
                "expected_answer_contains": ["30"],
                "baseline_tokens": 30,
            },
        },
    )
    assert quality_score == pytest.approx(1.0)
    assert efficiency_score == pytest.approx(1.0)
    assert details["baseline_tokens"] == 30
    assert details["tool_calls"] == ["calculator"]
