"""Prompt and context optimization helpers."""

from __future__ import annotations

from typing import Any


def optimize_system_prompt(
    base_prompt: str,
    task_type: str,
    max_tokens: int = 500,
) -> str:
    """Optimize system prompt based on task type."""
    if task_type in ("simple_qa", "factual"):
        return "Answer concisely. Be direct and accurate."

    task_prompts = {
        "code": "Write clean, efficient code. No explanations unless asked.",
        "math": "Solve step by step. Show your work.",
        "creative": base_prompt,
    }

    return task_prompts.get(task_type, base_prompt)


def truncate_context_intelligently(
    messages: list[Any],
    max_tokens: int = 8000,
) -> list[Any]:
    """
    Intelligently truncate conversation context to reduce tokens.

    Keeps: system message, first user message, and the last three exchanges.
    """
    if not messages:
        return messages

    def _role(message: Any) -> str:
        if isinstance(message, dict):
            return str(message.get("role", ""))
        role = getattr(message, "role", "")
        return str(role.value if hasattr(role, "value") else role)

    system_messages = [m for m in messages if _role(m) == "system"]
    other_messages = [m for m in messages if _role(m) != "system"]

    if len(other_messages) <= 6:
        return messages

    kept = system_messages + [other_messages[0]] + other_messages[-6:]
    return kept
