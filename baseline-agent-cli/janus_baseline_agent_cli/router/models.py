"""Model registry and routing helpers for the composite router."""

from __future__ import annotations

from dataclasses import dataclass

from janus_baseline_agent_cli.routing import (
    AGENT_KIMI_MODEL_ID,
    AGENT_NEMOTRON_MODEL_ID,
    FAST_KIMI_MODEL_ID,
    FAST_NEMOTRON_MODEL_ID,
    FAST_QWEN_MODEL_ID,
    RoutingDecision,
)


@dataclass
class ModelConfig:
    """Configuration for a backend model."""

    model_id: str
    display_name: str
    priority: int
    max_tokens: int = 8192
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    timeout_seconds: float = 120.0


# Build unique set of model configs from routing constants
_ALL_MODEL_CONFIGS: list[tuple[str, ModelConfig]] = [
    (FAST_QWEN_MODEL_ID, ModelConfig(
        model_id=FAST_QWEN_MODEL_ID,
        display_name="Qwen3 Next 80B",
        priority=1,
        max_tokens=8192,
        timeout_seconds=60.0,
    )),
    (FAST_NEMOTRON_MODEL_ID, ModelConfig(
        model_id=FAST_NEMOTRON_MODEL_ID,
        display_name="MiMo V2 Flash",
        priority=2,
        max_tokens=4096,
        timeout_seconds=30.0,
    )),
    (FAST_KIMI_MODEL_ID, ModelConfig(
        model_id=FAST_KIMI_MODEL_ID,
        display_name="Qwen3 VL 235B",
        priority=3,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=90.0,
    )),
    (AGENT_KIMI_MODEL_ID, ModelConfig(
        model_id=AGENT_KIMI_MODEL_ID,
        display_name="MiniMax M2.5",
        priority=4,
        max_tokens=16384,
        timeout_seconds=90.0,
    )),
]

MODEL_CONFIGS: dict[str, ModelConfig] = {}
for _model_id, _config in _ALL_MODEL_CONFIGS:
    MODEL_CONFIGS.setdefault(_model_id, _config)

DECISION_MODEL_IDS: dict[RoutingDecision, str] = {
    RoutingDecision.FAST_QWEN: FAST_QWEN_MODEL_ID,
    RoutingDecision.FAST_NEMOTRON: FAST_NEMOTRON_MODEL_ID,
    RoutingDecision.FAST_KIMI: FAST_KIMI_MODEL_ID,
    RoutingDecision.AGENT_NEMOTRON: AGENT_NEMOTRON_MODEL_ID,
    RoutingDecision.AGENT_KIMI: AGENT_KIMI_MODEL_ID,
}

FALLBACK_MODELS: dict[str, list[str]] = {
    FAST_QWEN_MODEL_ID: [FAST_NEMOTRON_MODEL_ID, FAST_KIMI_MODEL_ID],
    FAST_NEMOTRON_MODEL_ID: [FAST_QWEN_MODEL_ID, FAST_KIMI_MODEL_ID],
    FAST_KIMI_MODEL_ID: [FAST_QWEN_MODEL_ID, FAST_NEMOTRON_MODEL_ID],
    AGENT_KIMI_MODEL_ID: [FAST_KIMI_MODEL_ID, FAST_QWEN_MODEL_ID],
}


def get_model_for_decision(decision: RoutingDecision) -> ModelConfig:
    """Get the primary model for a routing decision."""
    model_id = DECISION_MODEL_IDS[decision]
    return MODEL_CONFIGS[model_id]


def get_fallback_models(primary_model_id: str) -> list[ModelConfig]:
    """Get fallback models when primary fails."""
    fallback_ids = FALLBACK_MODELS.get(primary_model_id, [])
    return [MODEL_CONFIGS[model_id] for model_id in fallback_ids if model_id in MODEL_CONFIGS]
