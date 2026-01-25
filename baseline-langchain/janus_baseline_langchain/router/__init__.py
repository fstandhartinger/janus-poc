"""Composite model router for LangChain baseline."""

from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.router.classifier import TaskClassifier
from janus_baseline_langchain.router.models import (
    MODEL_REGISTRY,
    ModelConfig,
    TaskType,
    get_fallback_models,
    get_model_for_task,
)

__all__ = [
    "CompositeRoutingChatModel",
    "ModelConfig",
    "MODEL_REGISTRY",
    "TaskClassifier",
    "TaskType",
    "get_fallback_models",
    "get_model_for_task",
]
