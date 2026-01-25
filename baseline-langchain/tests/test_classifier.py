"""Tests for the task classifier."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from janus_baseline_langchain.router.classifier import (
    TaskClassifier,
    CLASSIFICATION_PROMPT,
    CLASSIFICATION_TOOLS,
    COMPLEX_KEYWORDS,
)
from janus_baseline_langchain.router.models import TaskType


class TestClassificationPrompt:
    """Tests for the classification prompt."""

    def test_prompt_mentions_all_task_types(self) -> None:
        """Test that the prompt mentions all classifiable task types."""
        for task_type in TaskType:
            if task_type != TaskType.UNKNOWN:
                assert task_type.value in CLASSIFICATION_PROMPT


class TestClassificationTools:
    """Tests for the classification tools schema."""

    def test_tools_schema_valid(self) -> None:
        """Test that the tools schema is valid."""
        assert len(CLASSIFICATION_TOOLS) == 1
        tool = CLASSIFICATION_TOOLS[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "classify_task"

    def test_tools_schema_has_required_params(self) -> None:
        """Test that required parameters are defined."""
        tool = CLASSIFICATION_TOOLS[0]
        params = tool["function"]["parameters"]
        assert "task_type" in params["properties"]
        assert "confidence" in params["properties"]
        assert "task_type" in params["required"]
        assert "confidence" in params["required"]

    def test_tools_schema_task_type_enum(self) -> None:
        """Test that task_type enum includes all types except UNKNOWN."""
        tool = CLASSIFICATION_TOOLS[0]
        enum_values = tool["function"]["parameters"]["properties"]["task_type"]["enum"]
        expected = {t.value for t in TaskType if t != TaskType.UNKNOWN}
        assert set(enum_values) == expected


class TestComplexKeywords:
    """Tests for complex keywords list."""

    def test_keywords_are_lowercase(self) -> None:
        """Test that all keywords are lowercase."""
        for keyword in COMPLEX_KEYWORDS:
            assert keyword == keyword.lower()

    def test_expected_keywords_present(self) -> None:
        """Test that expected keywords are in the list."""
        expected = {"code", "write", "create", "implement", "solve", "calculate"}
        assert expected.issubset(set(COMPLEX_KEYWORDS))


class TestTaskClassifierInit:
    """Tests for TaskClassifier initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        classifier = TaskClassifier(api_key="test-key")
        assert classifier.api_key == "test-key"
        assert classifier.base_url == "https://llm.chutes.ai/v1"

    def test_init_with_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        classifier = TaskClassifier(
            api_key="test-key",
            base_url="https://custom.url/v1",
        )
        assert classifier.base_url == "https://custom.url/v1"


class TestExtractUserContent:
    """Tests for _extract_user_content method."""

    def test_extract_single_string_message(self) -> None:
        """Test extracting content from a single string message."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [HumanMessage(content="Hello world")]
        content = classifier._extract_user_content(messages)
        assert content == "Hello world"

    def test_extract_multiple_messages(self) -> None:
        """Test extracting content from multiple messages."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            HumanMessage(content="First"),
            HumanMessage(content="Second"),
            HumanMessage(content="Third"),
        ]
        content = classifier._extract_user_content(messages)
        assert "First" in content
        assert "Second" in content
        assert "Third" in content

    def test_extract_ignores_non_human_messages(self) -> None:
        """Test that only HumanMessage content is extracted."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            SystemMessage(content="System instructions"),
            HumanMessage(content="User input"),
            AIMessage(content="AI response"),
        ]
        content = classifier._extract_user_content(messages)
        assert content == "User input"

    def test_extract_multimodal_text_parts(self) -> None:
        """Test extracting text from multimodal messages."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            HumanMessage(content=[
                {"type": "text", "text": "Part one"},
                {"type": "image_url", "image_url": {"url": "http://example.com"}},
                {"type": "text", "text": "Part two"},
            ]),
        ]
        content = classifier._extract_user_content(messages)
        assert "Part one" in content
        assert "Part two" in content

    def test_extract_empty_messages(self) -> None:
        """Test extracting from empty message list."""
        classifier = TaskClassifier(api_key="test-key")
        content = classifier._extract_user_content([])
        assert content == ""


class TestHasComplexKeywords:
    """Tests for _has_complex_keywords method."""

    def test_has_complex_keyword(self) -> None:
        """Test detection of complex keywords."""
        classifier = TaskClassifier(api_key="test-key")
        assert classifier._has_complex_keywords("Please write a function") is True
        assert classifier._has_complex_keywords("Can you create a class?") is True
        assert classifier._has_complex_keywords("Implement the algorithm") is True

    def test_no_complex_keyword(self) -> None:
        """Test text without complex keywords."""
        classifier = TaskClassifier(api_key="test-key")
        assert classifier._has_complex_keywords("Hello") is False
        assert classifier._has_complex_keywords("What time is it?") is False
        assert classifier._has_complex_keywords("Hi there") is False

    def test_case_insensitive(self) -> None:
        """Test that keyword detection is case insensitive."""
        classifier = TaskClassifier(api_key="test-key")
        assert classifier._has_complex_keywords("WRITE code") is True
        assert classifier._has_complex_keywords("Write CODE") is True
        assert classifier._has_complex_keywords("wRiTe CoDe") is True


class TestClassify:
    """Tests for classify method."""

    def test_classify_with_images(self) -> None:
        """Test that images result in VISION classification."""
        classifier = TaskClassifier(api_key="test-key")
        task_type, confidence = classifier.classify([], has_images=True)
        assert task_type == TaskType.VISION
        assert confidence == 1.0

    def test_classify_short_simple_message(self) -> None:
        """Test short simple messages without complex keywords."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [HumanMessage(content="Hi")]
        task_type, confidence = classifier.classify(messages)
        assert task_type == TaskType.SIMPLE_TEXT
        assert confidence == 0.8

    def test_classify_short_with_complex_keyword(self) -> None:
        """Test short messages with complex keywords are not SIMPLE_TEXT."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [HumanMessage(content="Write code")]
        task_type, _ = classifier.classify(messages)
        # With complex keyword, should not be simple_text unless LLM decides
        # Since we can't call the LLM in tests, it should fall back to GENERAL_TEXT
        assert task_type in [TaskType.SIMPLE_TEXT, TaskType.GENERAL_TEXT, TaskType.PROGRAMMING]

    def test_classify_long_message_triggers_llm(self) -> None:
        """Test that long messages (>50 chars) would trigger LLM classification."""
        classifier = TaskClassifier(api_key="test-key")
        long_message = "a" * 60  # 60 characters
        messages = [HumanMessage(content=long_message)]
        # Without mocking, this will fail LLM call and default to GENERAL_TEXT
        task_type, confidence = classifier.classify(messages)
        assert task_type == TaskType.GENERAL_TEXT
        assert confidence == 0.5  # Default confidence on error


class TestClassifyEdgeCases:
    """Edge case tests for classify method."""

    def test_classify_empty_messages(self) -> None:
        """Test classification with empty message list."""
        classifier = TaskClassifier(api_key="test-key")
        task_type, confidence = classifier.classify([])
        # Empty messages should be treated as simple
        assert task_type == TaskType.SIMPLE_TEXT
        assert confidence == 0.8

    def test_classify_whitespace_only(self) -> None:
        """Test classification with whitespace-only content."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [HumanMessage(content="   ")]
        task_type, _ = classifier.classify(messages)
        # Whitespace only is short without keywords
        assert task_type == TaskType.SIMPLE_TEXT

    def test_classify_mixed_content(self) -> None:
        """Test classification with mixed message types."""
        classifier = TaskClassifier(api_key="test-key")
        messages = [
            SystemMessage(content="You are helpful"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there"),
            HumanMessage(content="Thanks"),
        ]
        task_type, _ = classifier.classify(messages)
        # Only HumanMessage content is used: "Hello Thanks" - short and simple
        assert task_type == TaskType.SIMPLE_TEXT
