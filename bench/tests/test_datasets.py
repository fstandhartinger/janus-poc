"""Tests for dataset loading."""

import pytest

from janus_bench.datasets import get_tasks, load_suite
from janus_bench.models import Suite, TaskType


class TestDatasetLoader:
    """Tests for dataset loading functions."""

    def test_get_all_tasks(self):
        """Test getting all built-in tasks."""
        tasks = get_tasks()
        assert len(tasks) > 0

    def test_get_tasks_by_suite(self):
        """Test filtering tasks by suite."""
        train_tasks = get_tasks(suite=Suite.PUBLIC_TRAIN)
        dev_tasks = get_tasks(suite=Suite.PUBLIC_DEV)
        private_tasks = get_tasks(suite=Suite.PRIVATE_TEST)

        assert len(train_tasks) > 0
        assert len(dev_tasks) > 0
        assert len(private_tasks) > 0

        # All tasks should be in their respective suite
        assert all(t.suite == Suite.PUBLIC_TRAIN for t in train_tasks)
        assert all(t.suite == Suite.PUBLIC_DEV for t in dev_tasks)
        assert all(t.suite == Suite.PRIVATE_TEST for t in private_tasks)

    def test_get_tasks_by_type(self):
        """Test filtering tasks by type."""
        chat_tasks = get_tasks(task_type=TaskType.CHAT_QUALITY)
        coding_tasks = get_tasks(task_type=TaskType.CODING)
        streaming_tasks = get_tasks(task_type=TaskType.STREAMING)

        assert all(t.type == TaskType.CHAT_QUALITY for t in chat_tasks)
        assert all(t.type == TaskType.CODING for t in coding_tasks)
        assert all(t.type == TaskType.STREAMING for t in streaming_tasks)

    def test_get_tasks_combined_filter(self):
        """Test filtering by suite and type together."""
        tasks = get_tasks(suite=Suite.PUBLIC_DEV, task_type=TaskType.CHAT_QUALITY)

        assert len(tasks) > 0
        assert all(t.suite == Suite.PUBLIC_DEV for t in tasks)
        assert all(t.type == TaskType.CHAT_QUALITY for t in tasks)

    def test_load_suite_public_train(self):
        """Test loading public/train suite."""
        tasks = load_suite("public/train")
        assert len(tasks) > 0
        assert all(t.suite == Suite.PUBLIC_TRAIN for t in tasks)

    def test_load_suite_public_dev(self):
        """Test loading public/dev suite."""
        tasks = load_suite("public/dev")
        assert len(tasks) > 0
        assert all(t.suite == Suite.PUBLIC_DEV for t in tasks)

    def test_load_suite_invalid(self):
        """Test loading invalid suite raises error."""
        with pytest.raises(ValueError, match="Unknown suite"):
            load_suite("invalid/suite")

    def test_task_structure(self):
        """Test that tasks have required fields."""
        tasks = get_tasks()

        for task in tasks:
            assert task.id is not None
            assert task.suite is not None
            assert task.type is not None
            assert task.prompt is not None
            assert len(task.prompt) > 0

    def test_multimodal_tasks_have_images(self):
        """Test that multimodal tasks have image URLs."""
        multimodal_tasks = get_tasks(task_type=TaskType.MULTIMODAL)

        for task in multimodal_tasks:
            assert task.image_url is not None, f"Multimodal task {task.id} missing image_url"

    def test_private_tasks_are_stubs(self):
        """Test that private test tasks are marked as stubs."""
        private_tasks = get_tasks(suite=Suite.PRIVATE_TEST)

        for task in private_tasks:
            assert task.metadata is not None
            assert task.metadata.get("stub") is True
