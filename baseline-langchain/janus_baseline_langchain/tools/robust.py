"""Robust tool argument parsing helpers."""

from __future__ import annotations

import json
from typing import Any


def robust_parse_tool_call(raw_arguments: str | dict[str, Any]) -> dict[str, Any]:
    """Parse tool arguments with fallbacks for common formatting issues."""
    if isinstance(raw_arguments, dict):
        return raw_arguments

    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError:
        pass

    cleaned = raw_arguments.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    cleaned = cleaned.replace(",}", "}").replace(",]", "]")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": raw_arguments}
