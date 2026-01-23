"""Scoring functions for benchmark evaluation."""

from .quality import score_quality
from .research import (
    build_judge_prompt,
    detect_citations,
    detect_search_usage,
    extract_judge_score,
    parse_json_block,
    score_key_facts,
)
from .speed import score_speed
from .cost import score_cost
from .streaming import score_streaming
from .multimodal import score_multimodal
from .tool_use import (
    ToolSimulator,
    evaluate_code_execution,
    evaluate_function_call,
    evaluate_tool_chain,
    evaluate_tool_selection,
    score_tool_use,
)
from .composite import compute_composite_score, compute_task_scores

__all__ = [
    "score_quality",
    "score_speed",
    "score_cost",
    "score_streaming",
    "score_multimodal",
    "ToolSimulator",
    "evaluate_code_execution",
    "evaluate_function_call",
    "evaluate_tool_chain",
    "evaluate_tool_selection",
    "score_tool_use",
    "build_judge_prompt",
    "detect_citations",
    "detect_search_usage",
    "extract_judge_score",
    "parse_json_block",
    "score_key_facts",
    "compute_composite_score",
    "compute_task_scores",
]
