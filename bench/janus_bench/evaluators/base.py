"""Evaluation helpers for public benchmark datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    """Normalized evaluation outcome (0-1)."""

    score: float
    details: dict[str, Any]
    reasoning: str | None = None
