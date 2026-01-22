"""Pytest configuration and fixtures for janus-bench tests."""

import pytest

from janus_bench.config import Settings
from janus_bench.models import BenchmarkTask, Suite, TaskType


@pytest.fixture
def settings() -> Settings:
    """Provide test settings."""
    return Settings(
        target_url="http://localhost:8000",
        model="test-model",
        request_timeout=30,
    )


@pytest.fixture
def sample_task() -> BenchmarkTask:
    """Provide a sample benchmark task."""
    return BenchmarkTask(
        id="test_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.CHAT_QUALITY,
        prompt="What is 2 + 2?",
        expected_answer="4",
        expected_keywords=["4", "four"],
    )


@pytest.fixture
def sample_tasks() -> list[BenchmarkTask]:
    """Provide a list of sample benchmark tasks."""
    return [
        BenchmarkTask(
            id="test_001",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.CHAT_QUALITY,
            prompt="What is 2 + 2?",
            expected_answer="4",
        ),
        BenchmarkTask(
            id="test_002",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.STREAMING,
            prompt="Count from 1 to 5.",
            expected_keywords=["1", "2", "3", "4", "5"],
        ),
        BenchmarkTask(
            id="test_003",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.MULTIMODAL,
            prompt="Describe this image.",
            image_url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
        ),
    ]
