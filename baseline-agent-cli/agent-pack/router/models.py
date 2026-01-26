"""Model registry and routing helpers for the composite router."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """Task types for routing decisions."""

    SIMPLE_TEXT = "simple_text"
    GENERAL_TEXT = "general_text"
    MATH_REASONING = "math_reasoning"
    PROGRAMMING = "programming"
    CREATIVE = "creative"
    VISION = "vision"
    UNKNOWN = "unknown"


@dataclass
class ModelConfig:
    """Configuration for a backend model."""

    model_id: str
    display_name: str
    task_types: list[TaskType]
    priority: int
    max_tokens: int = 8192
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    timeout_seconds: float = 120.0


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "classifier": ModelConfig(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash (Classifier)",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=0,
        max_tokens=1024,
        timeout_seconds=5.0,  # Reduced from 10s - fail fast to fallback
    ),
    "fast": ModelConfig(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=1,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),
    "general": ModelConfig(
        model_id="zai-org/GLM-4.7-TEE",
        display_name="GLM 4.7",
        task_types=[TaskType.GENERAL_TEXT, TaskType.UNKNOWN],
        priority=2,
        max_tokens=8192,
        timeout_seconds=60.0,
    ),
    "reasoning": ModelConfig(
        model_id="deepseek-ai/DeepSeek-V3.2-Speciale-TEE",
        display_name="DeepSeek V3.2 Speciale",
        task_types=[TaskType.MATH_REASONING],
        priority=3,
        max_tokens=16384,
        timeout_seconds=120.0,
    ),
    "programming": ModelConfig(
        model_id="MiniMaxAI/MiniMax-M2.1-TEE",
        display_name="MiniMax M2.1",
        task_types=[TaskType.PROGRAMMING],
        priority=4,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),
    "creative": ModelConfig(
        model_id="deepseek-ai/DeepSeek-TNG-R1T2-Chimera",
        display_name="TNG R1T2 Chimera",
        task_types=[TaskType.CREATIVE],
        priority=5,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),
    "vision": ModelConfig(
        model_id="Qwen/Qwen3-VL-235B-A22B-Instruct",
        display_name="Qwen3 VL 235B",
        task_types=[TaskType.VISION],
        priority=6,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=90.0,
    ),
    "vision_fallback": ModelConfig(
        model_id="zai-org/GLM-4.6V",
        display_name="GLM 4.6V",
        task_types=[TaskType.VISION],
        priority=7,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=60.0,
    ),
    "fast_alt": ModelConfig(
        model_id="XiaomiMiMo/MiMo-V2-Flash",
        display_name="MiMo V2 Flash",
        task_types=[TaskType.SIMPLE_TEXT, TaskType.GENERAL_TEXT],
        priority=8,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),
}


def get_model_for_task(task_type: TaskType) -> ModelConfig:
    """Get the primary model for a task type."""
    for config in sorted(MODEL_REGISTRY.values(), key=lambda config: config.priority):
        if task_type in config.task_types:
            return config
    return MODEL_REGISTRY["general"]


def get_fallback_models(primary_model_id: str) -> list[ModelConfig]:
    """Get fallback models when primary fails."""
    primary = next(
        (config for config in MODEL_REGISTRY.values() if config.model_id == primary_model_id),
        None,
    )
    if not primary:
        return [MODEL_REGISTRY["general"]]

    fallbacks: list[ModelConfig] = []
    for config in sorted(MODEL_REGISTRY.values(), key=lambda config: config.priority):
        if config.model_id == primary_model_id:
            continue
        if primary.supports_vision and config.supports_vision:
            fallbacks.append(config)
        elif not primary.supports_vision and not config.supports_vision:
            fallbacks.append(config)

    return fallbacks[:3]
