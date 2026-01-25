"""Robust tool argument parsing helpers."""

from __future__ import annotations

import json
from typing import Any


def robust_parse_tool_call(raw_arguments: str | dict[str, Any]) -> dict[str, Any]:
    """
    Robust tool argument parsing with fallbacks.

    Attempts:
    1. Direct dict return when already parsed
    2. Standard JSON parse
    3. Clean common formatting errors
    """
    if isinstance(raw_arguments, dict):
        return raw_arguments

    # Try standard parse
    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError:
        pass

    cleaned = raw_arguments.strip()

    # Remove markdown code blocks
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    # Remove trailing commas
    cleaned = cleaned.replace(",}", "}").replace(",]", "]")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": raw_arguments}
