"""Simulated tool responses for benchmark evaluation."""

from __future__ import annotations

from typing import Any


class ToolSimulator:
    """Simulate tool responses for benchmark evaluation."""

    TOOL_RESPONSES = {
        "get_weather": lambda args: {
            "location": args.get("location"),
            "temperature": 22,
            "condition": "sunny",
            "units": args.get("units", "celsius"),
        },
        "web_search": lambda args: {
            "query": args.get("query"),
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."},
            ],
        },
        "calculator": lambda args: {
            "expression": args.get("expression"),
            "result": _safe_eval(args.get("expression", "0")),
        },
    }

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name in self.TOOL_RESPONSES:
            return {"success": True, "result": self.TOOL_RESPONSES[tool_name](arguments)}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}


def _safe_eval(expression: str) -> float:
    try:
        return float(eval(expression, {"__builtins__": {}}, {}))
    except Exception:
        return 0.0
