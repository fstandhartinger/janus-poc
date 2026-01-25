"""Composite routing chat model for LangChain."""

from __future__ import annotations

import logging
from typing import Any, Iterator, List, Optional, Sequence

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from janus_baseline_langchain.router.classifier import TaskClassifier
from janus_baseline_langchain.router.models import (
    MODEL_REGISTRY,
    ModelConfig,
    TaskType,
    get_fallback_models,
    get_model_for_task,
)

logger = logging.getLogger(__name__)


class CompositeRoutingChatModel(BaseChatModel):
    """
    A LangChain ChatModel that routes requests to optimal backend models.

    Features:
    - Classifies each request using a fast LLM
    - Routes to specialized models based on task type
    - Automatic fallback on errors (429, 5xx)
    - Full streaming support
    - Metrics tracking
    """

    api_key: str
    base_url: str = "https://llm.chutes.ai/v1"
    default_temperature: float = 0.7

    # Private attributes initialized in __init__
    _classifier: Optional[TaskClassifier] = None
    _model_cache: dict = {}
    _metrics: dict = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Use object.__setattr__ to bypass pydantic's setattr
        object.__setattr__(
            self, "_classifier", TaskClassifier(self.api_key, self.base_url)
        )
        object.__setattr__(self, "_model_cache", {})
        object.__setattr__(
            self,
            "_metrics",
            {
                "total_requests": 0,
                "fallback_count": 0,
                "by_task_type": {},
                "by_model": {},
                "errors": {},
            },
        )

    @property
    def _llm_type(self) -> str:
        return "composite-routing"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"base_url": self.base_url}

    def _get_model(self, config: ModelConfig) -> ChatOpenAI:
        """Get or create a ChatOpenAI instance for a model config."""
        if config.model_id not in self._model_cache:
            self._model_cache[config.model_id] = ChatOpenAI(
                model=config.model_id,
                api_key=SecretStr(self.api_key),
                base_url=self.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout_seconds,
                streaming=True,
            )
        return self._model_cache[config.model_id]

    def _detect_images(self, messages: Sequence[BaseMessage]) -> bool:
        """Check if messages contain image content."""
        for msg in messages:
            content = msg.content
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        return True
        return False

    def _update_metrics(
        self,
        task_type: TaskType,
        model_id: str,
        used_fallback: bool,
        error: Optional[str] = None,
    ) -> None:
        """Update routing metrics."""
        self._metrics["by_task_type"][task_type.value] = (
            self._metrics["by_task_type"].get(task_type.value, 0) + 1
        )
        self._metrics["by_model"][model_id] = (
            self._metrics["by_model"].get(model_id, 0) + 1
        )
        if used_fallback:
            self._metrics["fallback_count"] += 1
        if error:
            self._metrics["errors"][model_id] = (
                self._metrics["errors"].get(model_id, 0) + 1
            )

    def _should_retry(self, error_str: str) -> bool:
        """Check if error is retryable (rate limit or server error)."""
        return any(
            code in error_str
            for code in ("429", "rate", "500", "502", "503", "504")
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response by routing to the optimal model."""
        self._metrics["total_requests"] += 1

        has_images = self._detect_images(messages)
        task_type, confidence = self._classifier.classify(messages, has_images)

        primary_config = get_model_for_task(task_type)
        fallback_configs = get_fallback_models(primary_config.model_id, has_images)
        models_to_try = [primary_config] + fallback_configs

        logger.info(f"[Router] Task: {task_type.value} (confidence: {confidence:.2f})")
        logger.info(f"[Router] Primary model: {primary_config.display_name}")

        last_error: Optional[Exception] = None
        used_fallback = False

        for i, config in enumerate(models_to_try):
            try:
                model = self._get_model(config)
                result = model._generate(messages, stop, run_manager, **kwargs)

                self._update_metrics(task_type, config.model_id, used_fallback)
                return result

            except Exception as e:
                last_error = e
                used_fallback = True
                error_str = str(e).lower()

                self._update_metrics(
                    task_type, config.model_id, used_fallback=False, error=str(e)
                )

                if self._should_retry(error_str):
                    logger.warning(
                        f"[Router] Retryable error on {config.display_name}: {e}"
                    )
                    continue
                else:
                    logger.error(f"[Router] Error on {config.display_name}: {e}")
                    if i < len(models_to_try) - 1:
                        continue
                    raise

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream a response by routing to the optimal model."""
        self._metrics["total_requests"] += 1

        has_images = self._detect_images(messages)
        task_type, confidence = self._classifier.classify(messages, has_images)

        primary_config = get_model_for_task(task_type)
        fallback_configs = get_fallback_models(primary_config.model_id, has_images)
        models_to_try = [primary_config] + fallback_configs

        logger.info(f"[Router] Task: {task_type.value} (confidence: {confidence:.2f})")
        logger.info(f"[Router] Primary model: {primary_config.display_name}")

        last_error: Optional[Exception] = None
        used_fallback = False

        for i, config in enumerate(models_to_try):
            try:
                model = self._get_model(config)
                self._update_metrics(task_type, config.model_id, used_fallback)

                yield from model._stream(messages, stop, run_manager, **kwargs)
                return

            except Exception as e:
                last_error = e
                used_fallback = True
                error_str = str(e).lower()

                self._update_metrics(
                    task_type, config.model_id, used_fallback=False, error=str(e)
                )

                if self._should_retry(error_str):
                    logger.warning(
                        f"[Router] Retryable error on {config.display_name}: {e}"
                    )
                    continue
                else:
                    logger.error(f"[Router] Error on {config.display_name}: {e}")
                    if i < len(models_to_try) - 1:
                        continue
                    raise

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    def get_metrics(self) -> dict[str, Any]:
        """Get routing metrics."""
        total = max(self._metrics["total_requests"], 1)
        return {
            **self._metrics,
            "fallback_rate": self._metrics["fallback_count"] / total,
        }

    def bind_tools(
        self, tools: List[Any], **kwargs: Any
    ) -> "CompositeRoutingChatModel":
        """Bind tools - delegates to underlying models."""
        return self
