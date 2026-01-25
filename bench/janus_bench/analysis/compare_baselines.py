"""Helpers for comparing baseline benchmark reports."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .performance_report import compare_baselines


def compare_baselines_report(cli_report: str, langchain_report: str) -> dict[str, Any]:
    """Compare baselines and return JSON-serializable output."""
    comparison = compare_baselines(cli_report, langchain_report)
    return {
        "winner_by_category": comparison["winner_by_category"],
        "deltas": comparison["deltas"],
        "cli_metrics": asdict(comparison["cli_metrics"]),
        "langchain_metrics": asdict(comparison["langchain_metrics"]),
    }
