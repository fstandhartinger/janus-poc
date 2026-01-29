"""Code evaluator for public benchmark tasks."""

from __future__ import annotations

import re
from typing import Any

from .base import EvaluationResult


CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
DEF_RE = re.compile(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _extract_code(response_text: str) -> str:
    match = CODE_BLOCK_RE.search(response_text)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def _infer_function_name(code: str) -> str | None:
    match = DEF_RE.search(code)
    if match:
        return match.group(1)
    return None


def _compare(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float) and isinstance(actual, (int, float)):
        return abs(actual - expected) < 1e-6
    return actual == expected


def evaluate_code(
    response_text: str | None,
    expected: dict[str, Any],
) -> EvaluationResult:
    response_text = response_text or ""
    if not response_text.strip():
        return EvaluationResult(score=0.0, details={"reason": "empty_response"})

    language = expected.get("language")
    if language and str(language).lower() != "python":
        return EvaluationResult(score=0.0, details={"reason": "unsupported_language"})

    code = _extract_code(response_text)
    function_name = expected.get("function_name") or _infer_function_name(code)
    test_cases = expected.get("test_cases") if isinstance(expected.get("test_cases"), list) else []

    if not function_name or not test_cases:
        return EvaluationResult(score=0.0, details={"reason": "missing_tests_or_function"})

    namespace: dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    local_env: dict[str, Any] = {}

    try:
        exec(code, namespace, local_env)
    except Exception as exc:
        return EvaluationResult(score=0.0, details={"reason": "exec_failed", "error": str(exc)})

    func = local_env.get(function_name) or namespace.get(function_name)
    if not callable(func):
        return EvaluationResult(score=0.0, details={"reason": "function_missing"})

    passed = 0
    results: list[dict[str, Any]] = []
    for case in test_cases:
        args = case.get("input") if isinstance(case, dict) else None
        expected_output = case.get("output") if isinstance(case, dict) else None
        if not isinstance(args, list):
            results.append({"passed": False, "error": "invalid_args"})
            continue
        try:
            output = func(*args)
            success = _compare(output, expected_output)
            results.append({"passed": success, "output": output, "expected": expected_output})
            if success:
                passed += 1
        except Exception as exc:
            results.append({"passed": False, "error": str(exc)})

    score = passed / len(test_cases) if test_cases else 0.0
    details = {
        "passed": passed,
        "total": len(test_cases),
        "results": results,
    }
    return EvaluationResult(score=score, details=details)
