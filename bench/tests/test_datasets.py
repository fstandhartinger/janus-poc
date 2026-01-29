"""Tests for dataset loading."""

from collections import Counter

import pytest

from janus_bench.benchmarks import get_janus_benchmark_names
from janus_bench.datasets import get_tasks, load_suite, private_dataset_available
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
        tool_use_tasks = get_tasks(task_type=TaskType.TOOL_USE)
        cost_tasks = get_tasks(task_type=TaskType.COST)

        assert all(t.type == TaskType.CHAT_QUALITY for t in chat_tasks)
        assert all(t.type == TaskType.CODING for t in coding_tasks)
        assert all(t.type == TaskType.STREAMING for t in streaming_tasks)
        assert all(t.type == TaskType.TOOL_USE for t in tool_use_tasks)
        assert all(t.type == TaskType.COST for t in cost_tasks)

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

    def test_public_train_has_minimum_size(self):
        """Ensure public train has at least 100 tasks."""
        tasks = get_tasks(suite=Suite.PUBLIC_TRAIN)
        assert len(tasks) >= 100

    def test_public_dev_has_minimum_size(self):
        """Ensure public dev has at least 50 tasks."""
        tasks = get_tasks(suite=Suite.PUBLIC_DEV)
        assert len(tasks) >= 50

    def test_public_dataset_categories_covered(self):
        """Ensure public dataset covers all required categories."""
        tasks = get_tasks(suite=Suite.PUBLIC_TRAIN)
        categories = {
            task.metadata.get("category")
            for task in tasks
            if task.metadata and task.metadata.get("category")
        }
        assert {
            "chat",
            "research",
            "code",
            "multimodal",
            "agentic",
            "deep_research",
        }.issubset(categories)

    def test_load_suite_public_dev(self):
        """Test loading public/dev suite."""
        tasks = load_suite("public/dev")
        assert len(tasks) > 0
        assert all(t.suite == Suite.PUBLIC_DEV for t in tasks)

    def test_load_suite_janus_intelligence(self):
        """Test loading Janus intelligence suite."""
        tasks = load_suite("janus/intelligence")
        assert len(tasks) > 0
        assert all(t.suite == Suite.JANUS_INTELLIGENCE for t in tasks)

    def test_load_suite_invalid(self):
        """Test loading invalid suite raises error."""
        with pytest.raises(ValueError, match="Unknown suite"):
            load_suite("invalid/suite")

    def test_load_suite_janus_intelligence(self):
        """Test loading Janus intelligence suite."""
        tasks = load_suite("janus/intelligence")
        assert len(tasks) > 0
        assert all(t.suite == Suite.JANUS_INTELLIGENCE for t in tasks)

    def test_task_structure(self):
        """Test that tasks have required fields."""
        tasks = get_tasks()

        for task in tasks:
            assert task.id is not None
            assert task.benchmark is not None
            assert task.suite is not None
            assert task.type is not None
            assert task.prompt is not None
            assert len(task.prompt) > 0

    def test_multimodal_tasks_have_images(self):
        """Test that multimodal tasks have image URLs."""
        multimodal_tasks = get_tasks(task_type=TaskType.MULTIMODAL)

        for task in multimodal_tasks:
            subtype = None
            if task.metadata:
                subtype = task.metadata.get("multimodal_task_type")
            if subtype == "image_understanding":
                assert task.image_url is not None, (
                    f"Multimodal task {task.id} missing image_url"
                )
            if subtype == "mixed_media":
                messages = task.metadata.get("messages") if task.metadata else None
                has_message_image = False
                if isinstance(messages, list):
                    for message in messages:
                        content = message.get("content") if isinstance(message, dict) else None
                        if isinstance(content, list):
                            has_message_image = any(
                                part.get("type") == "image_url"
                                for part in content
                                if isinstance(part, dict)
                            )
                        if has_message_image:
                            break
                assert has_message_image, f"Mixed media task {task.id} missing image content"

    def test_private_tasks_are_stubs(self):
        """Test that private test tasks are marked as stubs."""
        private_tasks = get_tasks(suite=Suite.PRIVATE_TEST)
        assert len(private_tasks) > 0

        if private_dataset_available():
            assert all(
                not (task.metadata and task.metadata.get("stub"))
                for task in private_tasks
            )
        else:
            for task in private_tasks:
                assert task.metadata is not None
                assert task.metadata.get("stub") is True

    def test_subset_sampling_is_deterministic(self):
        """Test deterministic subset sampling with a seed."""
        tasks_full = load_suite("janus/intelligence", subset_percent=100, seed=123)
        tasks_sample_a = load_suite("janus/intelligence", subset_percent=10, seed=123)
        tasks_sample_b = load_suite("janus/intelligence", subset_percent=10, seed=123)

        assert len(tasks_full) > len(tasks_sample_a) > 0
        assert [t.id for t in tasks_sample_a] == [t.id for t in tasks_sample_b]

    def test_subset_sampling_deterministic(self):
        """Test subset sampling is deterministic by seed."""
        tasks_a = get_tasks(suite=Suite.PUBLIC_DEV, subset_percent=10, seed=123)
        tasks_b = get_tasks(suite=Suite.PUBLIC_DEV, subset_percent=10, seed=123)

        assert [t.id for t in tasks_a] == [t.id for t in tasks_b]

    def test_subset_sampling_preserves_janus_benchmarks(self):
        """Ensure each Janus benchmark appears in sampled subset."""
        tasks = get_tasks(suite=Suite.JANUS_INTELLIGENCE, subset_percent=5, seed=42)
        janus_names = set(get_janus_benchmark_names())
        found = {task.benchmark for task in tasks if task.benchmark in janus_names}

        assert janus_names.issubset(found)

    def test_research_task_type_breakdown(self):
        """Ensure research tasks include 5 subtypes with 20 items each."""
        tasks = get_tasks(suite=Suite.JANUS_INTELLIGENCE, benchmark="janus_research")

        assert len(tasks) == 100
        counts = Counter(task.metadata.get("research_task_type") for task in tasks)
        assert counts == {
            "fact_verification": 20,
            "current_events": 20,
            "comparative": 20,
            "synthesis": 20,
            "deep_dive": 20,
        }

        for task in tasks:
            assert task.metadata is not None
            assert "evaluation" in task.metadata

    def test_tool_use_task_type_breakdown(self):
        """Ensure tool-use tasks include 4 subtypes with required counts."""
        tasks = get_tasks(suite=Suite.JANUS_INTELLIGENCE, benchmark="janus_tool_use")

        assert len(tasks) == 80
        counts = Counter(task.metadata.get("tool_use_task_type") for task in tasks)
        assert counts == {
            "function_calling": 25,
            "tool_selection": 20,
            "tool_chaining": 20,
            "code_execution": 15,
        }

        for task in tasks:
            assert task.metadata is not None
            assert "available_tools" in task.metadata

    def test_multimodal_task_type_breakdown(self):
        """Ensure multimodal tasks include 4 subtypes with required counts."""
        tasks = get_tasks(suite=Suite.JANUS_INTELLIGENCE, benchmark="janus_multimodal")

        assert len(tasks) == 60
        counts = Counter(task.metadata.get("multimodal_task_type") for task in tasks)
        assert counts == {
            "image_generation": 20,
            "image_understanding": 20,
            "mixed_media": 10,
            "modality_routing": 10,
        }

        for task in tasks:
            assert task.metadata is not None
            assert "evaluation" in task.metadata
