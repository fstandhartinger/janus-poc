"""Tests for tool use scoring helpers."""

from janus_bench.scorers import (
    evaluate_code_execution,
    evaluate_function_call,
    evaluate_tool_chain,
    evaluate_tool_selection,
    score_tool_use,
)


def test_function_call_perfect_match():
    expected = {"function": "get_weather", "arguments": {"location": "Tokyo"}}
    actual = {"function": "get_weather", "arguments": {"location": "Tokyo"}}
    score, _ = evaluate_function_call(expected, actual)
    assert score == 1.0


def test_function_call_missing_arg():
    expected = {"function": "get_weather", "arguments": {"location": "Tokyo"}}
    actual = {"function": "get_weather", "arguments": {}}
    score, reasoning = evaluate_function_call(expected, actual)
    assert score == 0.3
    assert "Missing" in reasoning


def test_tool_selection_primary_tool():
    score, _ = evaluate_tool_selection(
        expected_tools=["calculator"],
        actual_tools=["calculator"],
        acceptable_alternatives=["code_execute"],
    )
    assert score == 1.0


def test_tool_selection_alternative():
    score, _ = evaluate_tool_selection(
        expected_tools=["calculator"],
        actual_tools=["code_execute"],
        acceptable_alternatives=["code_execute"],
    )
    assert score == 0.8


def test_tool_chain_partial_credit():
    score, reasoning = evaluate_tool_chain(
        expected_sequence=["web_search", "calculator"],
        actual_sequence=["web_search"],
        partial_credit=True,
    )
    assert score == 0.5
    assert "Partial" in reasoning


def test_code_execution_detects_output():
    score, reasoning = evaluate_code_execution(
        expected_output_contains=["2", "3"],
        response_text="Results: 2 3 5 7",
        tool_calls=[{"function": "code_execute", "arguments": {"code": "print('ok')"}}],
    )
    assert score == 1.0
    assert "Found" in reasoning


def test_score_tool_use_function_calling():
    metadata = {
        "tool_use_task_type": "function_calling",
        "expected_call": {"function": "get_weather", "arguments": {"location": "Tokyo"}},
        "evaluation": {"allow_extra_args": True},
    }
    score, reasoning = score_tool_use(
        response_text="",
        tool_calls=[{"function": "get_weather", "arguments": {"location": "Tokyo"}}],
        metadata=metadata,
    )
    assert score == 1.0
    assert "Perfect" in reasoning
