"""Tests for the composite model router."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from janus_baseline_langchain.router.models import (
    MODEL_REGISTRY,
    ModelConfig,
    TaskType,
    get_fallback_models,
    get_model_for_task,
)
from janus_baseline_langchain.router.classifier import TaskClassifier, COMPLEX_KEYWORDS
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_task_types_exist(self) -> None:
        """Verify all expected task types are defined."""
        expected = {
            "simple_text",
            "general_text",
            "math_reasoning",
            "programming",
            "creative",
            "vision",
            "unknown",
        }
        actual = {t.value for t in TaskType}
        assert expected == actual


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_model_config_defaults(self) -> None:
        """Test default values for ModelConfig."""
        config = ModelConfig(
            model_id="test/model",
            display_name="Test Model",
            task_types=[TaskType.GENERAL_TEXT],
            priority=1,
        )
        assert config.max_tokens == 8192
        assert config.supports_streaming is True
        assert config.supports_tools is True
        assert config.supports_vision is False
        assert config.timeout_seconds == 120.0
        assert config.temperature == 0.7


class TestModelRegistry:
    """Tests for the model registry."""

    def test_registry_has_required_models(self) -> None:
        """Test that all required model roles are present."""
        required_roles = {
            "classifier",
            "fast",
            "general",
            "reasoning",
            "programming",
            "creative",
            "vision",
            "vision_fallback",
        }
        assert required_roles.issubset(set(MODEL_REGISTRY.keys()))

    def test_classifier_model_config(self) -> None:
        """Test classifier model has correct configuration."""
        config = MODEL_REGISTRY["classifier"]
        assert config.temperature == 0.0
        assert config.max_tokens == 1024
        assert config.timeout_seconds <= 15.0

    def test_vision_models_support_vision(self) -> None:
        """Test vision models have supports_vision=True."""
        assert MODEL_REGISTRY["vision"].supports_vision is True
        assert MODEL_REGISTRY["vision_fallback"].supports_vision is True

    def test_non_vision_models_dont_support_vision(self) -> None:
        """Test non-vision models have supports_vision=False."""
        non_vision_roles = ["fast", "general", "reasoning", "programming", "creative"]
        for role in non_vision_roles:
            assert MODEL_REGISTRY[role].supports_vision is False


class TestGetModelForTask:
    """Tests for get_model_for_task function."""

    def test_simple_text_returns_fast_model(self) -> None:
        """Test simple text routes to fast model."""
        config = get_model_for_task(TaskType.SIMPLE_TEXT)
        assert TaskType.SIMPLE_TEXT in config.task_types

    def test_math_reasoning_returns_reasoning_model(self) -> None:
        """Test math reasoning routes to reasoning model."""
        config = get_model_for_task(TaskType.MATH_REASONING)
        assert TaskType.MATH_REASONING in config.task_types

    def test_programming_returns_programming_model(self) -> None:
        """Test programming routes to programming model."""
        config = get_model_for_task(TaskType.PROGRAMMING)
        assert TaskType.PROGRAMMING in config.task_types

    def test_creative_returns_creative_model(self) -> None:
        """Test creative routes to creative model."""
        config = get_model_for_task(TaskType.CREATIVE)
        assert TaskType.CREATIVE in config.task_types

    def test_vision_returns_vision_model(self) -> None:
        """Test vision routes to vision model."""
        config = get_model_for_task(TaskType.VISION)
        assert TaskType.VISION in config.task_types
        assert config.supports_vision is True

    def test_unknown_returns_general_model(self) -> None:
        """Test unknown routes to general model."""
        config = get_model_for_task(TaskType.UNKNOWN)
        assert TaskType.UNKNOWN in config.task_types or config == MODEL_REGISTRY["general"]


class TestGetFallbackModels:
    """Tests for get_fallback_models function."""

    def test_fallback_excludes_primary(self) -> None:
        """Test fallback list excludes the primary model."""
        primary = MODEL_REGISTRY["fast"]
        fallbacks = get_fallback_models(primary.model_id)
        for fb in fallbacks:
            assert fb.model_id != primary.model_id

    def test_fallback_limit(self) -> None:
        """Test fallback list is limited to 3 models."""
        primary = MODEL_REGISTRY["fast"]
        fallbacks = get_fallback_models(primary.model_id)
        assert len(fallbacks) <= 3

    def test_vision_fallback_only_vision_models(self) -> None:
        """Test vision fallbacks only include vision models."""
        primary = MODEL_REGISTRY["vision"]
        fallbacks = get_fallback_models(primary.model_id, is_vision=True)
        for fb in fallbacks:
            assert fb.supports_vision is True

    def test_non_vision_fallback_excludes_vision(self) -> None:
        """Test non-vision fallbacks exclude vision models."""
        primary = MODEL_REGISTRY["fast"]
        fallbacks = get_fallback_models(primary.model_id, is_vision=False)
        for fb in fallbacks:
            assert fb.supports_vision is False


class TestTaskClassifier:
    """Tests for TaskClassifier."""

    def test_images_return_vision(self) -> None:
        """Test that has_images=True returns VISION task type."""
        classifier = TaskClassifier(api_key="test-key")
        task_type, confidence = classifier.classify([], has_images=True)
        assert task_type == TaskType.VISION
        assert confidence == 1.0

    def test_short_simple_message(self) -> None:
        """Test short simple messages return SIMPLE_TEXT."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [HumanMessage(content="Hello")]
        task_type, confidence = classifier.classify(messages)
        assert task_type == TaskType.SIMPLE_TEXT
        assert confidence == 0.8

    def test_complex_keywords_not_simple(self) -> None:
        """Test that complex keywords prevent SIMPLE_TEXT classification."""
        classifier = TaskClassifier(api_key="test-key")
        for keyword in COMPLEX_KEYWORDS[:3]:
            messages = [HumanMessage(content=f"Please {keyword} something")]
            task_type, _ = classifier.classify(messages)
            # Should not be simple_text due to complex keyword
            assert task_type != TaskType.SIMPLE_TEXT or len(f"Please {keyword} something") >= 50

    def test_extract_user_content(self) -> None:
        """Test extracting text from user messages."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            HumanMessage(content="First message"),
            HumanMessage(content="Second message"),
        ]
        content = classifier._extract_user_content(messages)
        assert "First message" in content
        assert "Second message" in content

    def test_extract_user_content_multimodal(self) -> None:
        """Test extracting text from multimodal messages."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            HumanMessage(content=[
                {"type": "text", "text": "What is in this image?"},
                {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
            ]),
        ]
        content = classifier._extract_user_content(messages)
        assert "What is in this image?" in content


class TestCompositeRoutingChatModel:
    """Tests for CompositeRoutingChatModel."""

    def test_llm_type(self) -> None:
        """Test _llm_type returns correct value."""
        model = CompositeRoutingChatModel(api_key="test-key")
        assert model._llm_type == "composite-routing"

    def test_identifying_params(self) -> None:
        """Test _identifying_params includes base_url."""
        model = CompositeRoutingChatModel(
            api_key="test-key",
            base_url="https://custom.url/v1",
        )
        params = model._identifying_params
        assert "base_url" in params
        assert params["base_url"] == "https://custom.url/v1"

    def test_metrics_initialization(self) -> None:
        """Test metrics are initialized correctly."""
        model = CompositeRoutingChatModel(api_key="test-key")
        metrics = model.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["fallback_count"] == 0
        assert metrics["fallback_rate"] == 0.0
        assert isinstance(metrics["by_task_type"], dict)
        assert isinstance(metrics["by_model"], dict)
        assert isinstance(metrics["errors"], dict)

    def test_detect_images_with_image_url(self) -> None:
        """Test image detection with image_url content."""
        model = CompositeRoutingChatModel(api_key="test-key")
        messages = [
            HumanMessage(content=[
                {"type": "text", "text": "What is this?"},
                {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
            ]),
        ]
        assert model._detect_images(messages) is True

    def test_detect_images_without_image(self) -> None:
        """Test image detection without images."""
        model = CompositeRoutingChatModel(api_key="test-key")
        messages = [HumanMessage(content="Hello world")]
        assert model._detect_images(messages) is False

    def test_should_retry_rate_limit(self) -> None:
        """Test _should_retry returns True for rate limit errors."""
        model = CompositeRoutingChatModel(api_key="test-key")
        assert model._should_retry("Error 429 rate limit exceeded") is True

    def test_should_retry_server_error(self) -> None:
        """Test _should_retry returns True for server errors."""
        model = CompositeRoutingChatModel(api_key="test-key")
        assert model._should_retry("Error 500 internal server error") is True
        assert model._should_retry("502 bad gateway") is True
        assert model._should_retry("503 service unavailable") is True

    def test_should_retry_other_error(self) -> None:
        """Test _should_retry returns False for other errors."""
        model = CompositeRoutingChatModel(api_key="test-key")
        assert model._should_retry("Authentication failed") is False
        assert model._should_retry("Invalid request") is False

    def test_bind_tools_returns_self(self) -> None:
        """Test bind_tools returns the model itself."""
        model = CompositeRoutingChatModel(api_key="test-key")
        result = model.bind_tools([])
        assert result is model

    def test_model_cache(self) -> None:
        """Test that models are cached."""
        model = CompositeRoutingChatModel(api_key="test-key")
        config = MODEL_REGISTRY["fast"]
        llm1 = model._get_model(config)
        llm2 = model._get_model(config)
        assert llm1 is llm2


class TestRouterIntegration:
    """Integration tests for the router (require mocking)."""

    @patch("janus_baseline_langchain.router.chat_model.ChatOpenAI")
    def test_generate_routes_to_correct_model(self, mock_chat_openai: MagicMock) -> None:
        """Test that _generate routes to the correct model based on task type."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.generations = [[MagicMock(text="Test response")]]
        mock_llm._generate.return_value = mock_result
        mock_chat_openai.return_value = mock_llm

        model = CompositeRoutingChatModel(api_key="test-key")
        messages = [HumanMessage(content="Hi")]

        # Should classify as simple_text and route accordingly
        with patch.object(model._classifier, "classify", return_value=(TaskType.SIMPLE_TEXT, 0.9)):
            model._generate(messages)

        assert model._metrics["total_requests"] == 1
        assert model._metrics["by_task_type"].get("simple_text", 0) == 1
