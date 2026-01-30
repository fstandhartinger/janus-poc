"""Shared routing decision definitions for Janus baseline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Optional

ROUTING_DECISION_KEY = "routing_decision"

DECISION_MODEL_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
FAST_QWEN_MODEL_ID = "Qwen/Qwen3-30B-A3B-Instruct-2507"
FAST_NEMOTRON_MODEL_ID = DECISION_MODEL_ID
FAST_KIMI_MODEL_ID = "moonshotai/Kimi-K2.5-TEE"
AGENT_NEMOTRON_MODEL_ID = DECISION_MODEL_ID
AGENT_KIMI_MODEL_ID = "moonshotai/Kimi-K2.5-TEE"


class RoutingDecision(str, Enum):
    """Routing decisions mapping to path + model."""

    FAST_QWEN = "fast_qwen"
    FAST_NEMOTRON = "fast_nemotron"
    FAST_KIMI = "fast_kimi"
    AGENT_NEMOTRON = "agent_nemotron"
    AGENT_KIMI = "agent_kimi"


@dataclass(frozen=True)
class DecisionDetails:
    path: Literal["fast", "agent"]
    model_id: str
    label: str


DECISION_DETAILS: dict[RoutingDecision, DecisionDetails] = {
    RoutingDecision.FAST_QWEN: DecisionDetails(
        path="fast",
        model_id=FAST_QWEN_MODEL_ID,
        label="FAST + Qwen3 30B (plain)",
    ),
    RoutingDecision.FAST_NEMOTRON: DecisionDetails(
        path="fast",
        model_id=FAST_NEMOTRON_MODEL_ID,
        label="FAST + Nemotron 30B (light reasoning)",
    ),
    RoutingDecision.FAST_KIMI: DecisionDetails(
        path="fast",
        model_id=FAST_KIMI_MODEL_ID,
        label="FAST + Kimi K2.5 (hard reasoning)",
    ),
    RoutingDecision.AGENT_NEMOTRON: DecisionDetails(
        path="agent",
        model_id=AGENT_NEMOTRON_MODEL_ID,
        label="AGENT + Nemotron 30B (simple agent task)",
    ),
    RoutingDecision.AGENT_KIMI: DecisionDetails(
        path="agent",
        model_id=AGENT_KIMI_MODEL_ID,
        label="AGENT + Kimi K2.5 (general agent task)",
    ),
}


ROUTING_DECISION_VALUES = [decision.value for decision in RoutingDecision]


ROUTING_DECISION_TOOL = {
    "type": "function",
    "function": {
        "name": "select_routing_decision",
        "description": "Select the routing decision that determines path and model.",
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ROUTING_DECISION_VALUES,
                    "description": "Routing decision enum value.",
                }
            },
            "required": ["decision"],
            "additionalProperties": False,
        },
    },
}

ROUTING_DECISION_PROMPT = """You are a routing verifier. Choose exactly one decision.

Decisions (path + model):
- fast_qwen: FAST path, Qwen/Qwen3-30B-A3B-Instruct-2507, plain short answers
- fast_nemotron: FAST path, nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16, light reasoning/longer answers
- fast_kimi: FAST path, moonshotai/Kimi-K2.5-TEE, harder reasoning without tools
- agent_nemotron: AGENT path, nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16, simple agent tasks
- agent_kimi: AGENT path, moonshotai/Kimi-K2.5-TEE, all other agent tasks

Rules:
- If tools or external actions are required, choose an AGENT decision.
- If tools are not required, choose a FAST decision.
- If images are present, choose *_kimi (fast_kimi or agent_kimi) based on tool need.

Images present: {has_images}
User request: {user_message}

Call select_routing_decision with your decision."""


def decision_from_metadata(metadata: Optional[dict[str, Any]]) -> Optional[RoutingDecision]:
    """Extract routing decision from metadata if present."""
    if not metadata:
        return None
    raw = metadata.get(ROUTING_DECISION_KEY)
    if isinstance(raw, str):
        try:
            return RoutingDecision(raw)
        except ValueError:
            return None
    return None


def decision_from_model_id(
    model_id: str, path_hint: Literal["fast", "agent"] | None = None
) -> Optional[RoutingDecision]:
    """Map explicit model IDs to routing decisions."""
    if model_id == FAST_QWEN_MODEL_ID:
        return RoutingDecision.FAST_QWEN
    if model_id == FAST_NEMOTRON_MODEL_ID:
        if path_hint == "agent":
            return RoutingDecision.AGENT_NEMOTRON
        return RoutingDecision.FAST_NEMOTRON
    if model_id == FAST_KIMI_MODEL_ID:
        if path_hint == "agent":
            return RoutingDecision.AGENT_KIMI
        return RoutingDecision.FAST_KIMI
    return None


def decision_requires_agent(decision: RoutingDecision) -> bool:
    return DECISION_DETAILS[decision].path == "agent"


def model_for_decision(decision: RoutingDecision) -> str:
    return DECISION_DETAILS[decision].model_id


def apply_decision_metadata(
    metadata: Optional[dict[str, Any]],
    decision: RoutingDecision,
) -> dict[str, Any]:
    """Return metadata with routing decision applied."""
    merged = dict(metadata or {})
    merged[ROUTING_DECISION_KEY] = decision.value
    return merged


def decision_for_images(is_agent: bool) -> RoutingDecision:
    return RoutingDecision.AGENT_KIMI if is_agent else RoutingDecision.FAST_KIMI


def coerce_decision_for_agent(decision: RoutingDecision) -> RoutingDecision:
    """Ensure decision uses agent path while preserving model when possible."""
    if decision == RoutingDecision.FAST_NEMOTRON:
        return RoutingDecision.AGENT_NEMOTRON
    if decision == RoutingDecision.FAST_KIMI:
        return RoutingDecision.AGENT_KIMI
    if decision == RoutingDecision.FAST_QWEN:
        return RoutingDecision.AGENT_NEMOTRON
    return decision
