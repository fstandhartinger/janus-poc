"""Tool-use benchmark scoring helpers."""

from __future__ import annotations

from typing import Any, Callable


CODE_TOOL_NAMES = {"code_execute", "execute_code", "run_code"}


class ToolSimulator:
    """Simulate tool responses for benchmark evaluation."""

    TOOL_RESPONSES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "get_weather": lambda args: {
            "location": args.get("location"),
            "temperature": 22,
            "condition": "sunny",
            "units": args.get("units", "celsius"),
        },
        "search": lambda args: {
            "query": args.get("query"),
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."},
            ],
        },
        "calculator": lambda args: {
            "expression": args.get("expression"),
            "result": eval(
                args.get("expression", "0"),
                {"__builtins__": {}},
                {},
            ),
        },
        "get_exchange_rate": lambda args: {
            "base_currency": args.get("base_currency"),
            "target_currency": args.get("target_currency"),
            "rate": 0.9,
        },
        "get_stock_price": lambda args: {
            "ticker": args.get("ticker"),
            "price": 150.0,
            "currency": "USD",
        },
        "convert_units": lambda args: {
            "value": args.get("value"),
            "from_unit": args.get("from_unit"),
            "to_unit": args.get("to_unit"),
            "result": args.get("value"),
        },
        "get_time": lambda args: {
            "timezone": args.get("timezone"),
            "time": "12:00",
        },
        "code_execute": lambda args: {
            "language": args.get("language", "python"),
            "output": args.get("code", "")[:128],
        },
    }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name in self.TOOL_RESPONSES:
            try:
                return {
                    "success": True,
                    "result": self.TOOL_RESPONSES[tool_name](arguments),
                }
            except Exception as exc:  # pragma: no cover - defensive fallback
                return {"success": False, "error": str(exc)}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


def evaluate_function_call(
    expected: dict[str, Any],
    actual: dict[str, Any],
    allow_extra_args: bool = True,
) -> tuple[float, str]:
    """Evaluate function call correctness."""
    if not expected or not actual:
        return 0.0, "Missing expected or actual function call"

    if expected.get("function") != actual.get("function"):
        return (
            0.0,
            f"Wrong function: expected {expected.get('function')}, got {actual.get('function')}",
        )

    expected_args = expected.get("arguments", {}) or {}
    actual_args = actual.get("arguments", {}) or {}

    missing: list[str] = []
    wrong: list[str] = []

    for key, value in expected_args.items():
        if key not in actual_args:
            missing.append(key)
        elif actual_args[key] != value:
            if isinstance(value, str) and isinstance(actual_args[key], str):
                if value.lower() not in actual_args[key].lower():
                    wrong.append(f"{key}: expected '{value}', got '{actual_args[key]}'")
            elif isinstance(value, str) or isinstance(actual_args[key], str):
                expected_str = str(value).lower()
                actual_str = str(actual_args[key]).lower()
                if expected_str not in actual_str and actual_str not in expected_str:
                    wrong.append(f"{key}: expected '{value}', got '{actual_args[key]}'")
            else:
                wrong.append(f"{key}: expected {value}, got {actual_args[key]}")

    if missing:
        return 0.3, f"Missing arguments: {missing}"

    if wrong:
        return 0.6, f"Wrong argument values: {wrong}"

    if not allow_extra_args:
        extra = set(actual_args.keys()) - set(expected_args.keys())
        if extra:
            return 0.9, f"Extra arguments (minor penalty): {sorted(extra)}"

    return 1.0, "Perfect match"


def evaluate_tool_selection(
    expected_tools: list[str],
    actual_tools: list[str],
    acceptable_alternatives: list[str] | None = None,
) -> tuple[float, str]:
    """Evaluate tool selection."""
    acceptable = set(expected_tools + (acceptable_alternatives or []))

    if not actual_tools:
        return 0.0, "No tools selected"

    if actual_tools[0] in expected_tools:
        return 1.0, "Correct tool selected"

    if actual_tools[0] in acceptable:
        return 0.8, f"Acceptable alternative: {actual_tools[0]}"

    for tool in actual_tools:
        if tool in acceptable:
            return 0.5, f"Found acceptable tool in selection: {tool}"

    return 0.0, f"Wrong tools selected: {actual_tools}"


def evaluate_tool_sequence(
    expected_sequence: list[str],
    actual_sequence: list[str],
    partial_credit: bool = True,
) -> tuple[float, str]:
    """Evaluate a sequence of tool calls."""
    if not expected_sequence:
        return 0.0, "Missing expected tool sequence"
    if not actual_sequence:
        return 0.0, "No tools called"

    matches = 0
    for index, expected_tool in enumerate(expected_sequence):
        if index < len(actual_sequence) and actual_sequence[index] == expected_tool:
            matches += 1

    if matches == len(expected_sequence):
        return 1.0, "Perfect sequence match"

    if not partial_credit:
        return 0.0, "Sequence mismatch"

    partial = matches / len(expected_sequence)
    return partial, f"Partial sequence match: {matches}/{len(expected_sequence)}"


def evaluate_code_execution(
    expected_output_contains: list[str],
    response_text: str,
    tool_calls: list[dict[str, Any]],
) -> tuple[float, str]:
    """Evaluate code execution tasks."""
    code_executed = any(
        call.get("function") in CODE_TOOL_NAMES for call in tool_calls
    )

    if not code_executed and "```" not in response_text:
        return 0.2, "No code execution detected"

    if not expected_output_contains:
        return 0.5, "No expected outputs specified"

    found = sum(1 for exp in expected_output_contains if exp in response_text)
    score = found / len(expected_output_contains)
    return score, f"Found {found}/{len(expected_output_contains)} expected outputs"


def evaluate_tool_chain(
    expected_sequence: list[str],
    actual_sequence: list[str],
    partial_credit: bool = True,
) -> tuple[float, str]:
    """Compatibility wrapper for tool chaining evaluation."""
    return evaluate_tool_sequence(expected_sequence, actual_sequence, partial_credit)


def _score_expected_outputs(response_text: str, expected_outputs: list[str]) -> float:
    if not expected_outputs:
        return 0.0
    found = sum(1 for exp in expected_outputs if exp in response_text)
    return found / len(expected_outputs)


def score_tool_use(
    response_text: str | None,
    tool_calls: list[dict[str, Any]],
    metadata: dict[str, Any] | None,
) -> tuple[float, str]:
    """Score tool-use tasks based on task subtype metadata."""
    response_text = response_text or ""
    metadata = metadata or {}
    task_type = (
        metadata.get("tool_use_task_type")
        or metadata.get("tool_task_type")
        or metadata.get("task_type")
        or "tool_use"
    )
    evaluation = metadata.get("evaluation") or {}

    if task_type == "function_calling":
        expected_call = metadata.get("expected_call", {})
        allow_extra = evaluation.get("allow_extra_args", True)
        if not tool_calls:
            return 0.0, "No function call made"
        return evaluate_function_call(expected_call, tool_calls[0], allow_extra)

    if task_type == "tool_selection":
        expected_tools = list(metadata.get("expected_tools") or [])
        alternatives = list(metadata.get("acceptable_alternatives") or [])
        actual_tools = [
            call.get("function") for call in tool_calls if call.get("function")
        ]
        return evaluate_tool_selection(expected_tools, actual_tools, alternatives)

    if task_type == "tool_chaining":
        expected_sequence = list(metadata.get("expected_sequence") or [])
        actual_sequence = [
            call.get("function") for call in tool_calls if call.get("function")
        ]
        partial_credit = evaluation.get("partial_credit", True)
        score, reasoning = evaluate_tool_sequence(
            expected_sequence,
            actual_sequence,
            partial_credit=partial_credit,
        )
        if evaluation.get("verify_final_answer"):
            expected_outputs = list(metadata.get("expected_output_contains") or [])
            if expected_outputs:
                answer_score = _score_expected_outputs(response_text, expected_outputs)
                score = (score + answer_score) / 2
                reasoning = f"{reasoning}; answer_score={answer_score:.2f}"
        return score, reasoning

    if task_type == "code_execution":
        expected_outputs = list(metadata.get("expected_output_contains") or [])
        return evaluate_code_execution(expected_outputs, response_text, tool_calls)

    return 0.0, f"Unknown tool-use task type: {task_type}"
