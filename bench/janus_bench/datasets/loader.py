"""Dataset loader for benchmark tasks."""

import json
import math
import random
from pathlib import Path
from typing import Optional

from ..adapters import list_adapters
from ..models import BenchmarkTask, Suite, TaskType

# Built-in benchmark tasks
BUILTIN_TASKS: list[BenchmarkTask] = [
    # Chat quality tasks (public/train)
    BenchmarkTask(
        id="chat_train_001",
        suite=Suite.PUBLIC_TRAIN,
        type=TaskType.CHAT_QUALITY,
        prompt="What is the capital of France?",
        expected_answer="Paris",
        expected_keywords=["Paris"],
    ),
    BenchmarkTask(
        id="chat_train_002",
        suite=Suite.PUBLIC_TRAIN,
        type=TaskType.CHAT_QUALITY,
        prompt="Explain photosynthesis in one sentence.",
        expected_keywords=["sunlight", "plants", "energy", "carbon dioxide", "oxygen"],
    ),
    BenchmarkTask(
        id="chat_train_003",
        suite=Suite.PUBLIC_TRAIN,
        type=TaskType.CHAT_QUALITY,
        prompt="What is 15 + 27?",
        expected_answer="42",
        expected_keywords=["42"],
    ),
    # Chat quality tasks (public/dev)
    BenchmarkTask(
        id="chat_dev_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.CHAT_QUALITY,
        prompt="What is the largest planet in our solar system?",
        expected_answer="Jupiter",
        expected_keywords=["Jupiter"],
    ),
    BenchmarkTask(
        id="chat_dev_002",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.CHAT_QUALITY,
        prompt="Write a haiku about coding.",
        expected_keywords=None,  # Subjective - just check for valid response
    ),
    # Research tasks (public/dev)
    BenchmarkTask(
        id="research_dev_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.RESEARCH,
        prompt="What year was Python first released?",
        expected_answer="1991",
        expected_keywords=["1991"],
    ),
    BenchmarkTask(
        id="research_dev_002",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.RESEARCH,
        prompt="Who created the Linux kernel?",
        expected_answer="Linus Torvalds",
        expected_keywords=["Linus", "Torvalds"],
    ),
    # Coding tasks (public/dev)
    BenchmarkTask(
        id="coding_dev_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.CODING,
        prompt="Write a Python function that returns the factorial of a number.",
        expected_keywords=["def", "factorial", "return"],
    ),
    BenchmarkTask(
        id="coding_dev_002",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.CODING,
        prompt="Write a Python function to check if a string is a palindrome.",
        expected_keywords=["def", "palindrome", "return"],
    ),
    # Streaming test tasks (public/dev)
    BenchmarkTask(
        id="streaming_dev_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.STREAMING,
        prompt="Count from 1 to 10, with each number on a new line.",
        expected_keywords=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
    ),
    BenchmarkTask(
        id="streaming_dev_002",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.STREAMING,
        prompt="List the first 5 prime numbers, one per line.",
        expected_keywords=["2", "3", "5", "7", "11"],
    ),
    # Multimodal tasks (public/dev) - placeholder with data URL image
    BenchmarkTask(
        id="multimodal_dev_001",
        suite=Suite.PUBLIC_DEV,
        type=TaskType.MULTIMODAL,
        prompt="Describe what you see in this image.",
        # A simple 1x1 red pixel PNG as base64 data URL for testing
        image_url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==",
        expected_keywords=None,  # Subjective
    ),
    # Private test stubs (placeholders)
    BenchmarkTask(
        id="private_test_001",
        suite=Suite.PRIVATE_TEST,
        type=TaskType.CHAT_QUALITY,
        prompt="[PRIVATE] This task is hidden for final evaluation.",
        expected_answer=None,
        metadata={"stub": True},
    ),
    BenchmarkTask(
        id="private_test_002",
        suite=Suite.PRIVATE_TEST,
        type=TaskType.CODING,
        prompt="[PRIVATE] This coding task is hidden for final evaluation.",
        expected_answer=None,
        metadata={"stub": True},
    ),
]


def get_tasks(
    suite: Optional[Suite] = None,
    task_type: Optional[TaskType] = None,
    benchmark: Optional[str] = None,
    subset_percent: int = 100,
    seed: Optional[int] = None,
) -> list[BenchmarkTask]:
    """Get benchmark tasks filtered by suite and/or type.

    Args:
        suite: Filter by benchmark suite (public/train, public/dev, private/test)
        task_type: Filter by task type (chat_quality, research, coding, etc.)
        benchmark: Filter by benchmark name/group
        subset_percent: Optional subset percentage (1-100)
        seed: Optional seed for deterministic sampling

    Returns:
        List of matching benchmark tasks
    """
    tasks = BUILTIN_TASKS.copy()
    tasks.extend(_load_janus_tasks())

    if suite is not None:
        tasks = [t for t in tasks if t.suite == suite]

    if task_type is not None:
        tasks = [t for t in tasks if t.type == task_type]

    if benchmark is not None:
        tasks = [t for t in tasks if t.benchmark == benchmark]

    if subset_percent < 100:
        tasks = _sample_tasks(tasks, subset_percent=subset_percent, seed=seed)

    return tasks


def load_suite(
    suite_name: str,
    custom_path: Optional[Path] = None,
    benchmark: Optional[str] = None,
    subset_percent: int = 100,
    seed: Optional[int] = None,
) -> list[BenchmarkTask]:
    """Load a benchmark suite by name.

    Args:
        suite_name: Suite name like "public/train" or "public/dev"
        custom_path: Optional path to custom dataset JSON file
        benchmark: Optional benchmark name/group
        subset_percent: Optional subset percentage (1-100)
        seed: Optional seed for deterministic sampling

    Returns:
        List of benchmark tasks for the suite
    """
    # Parse suite name
    try:
        suite = Suite(suite_name)
    except ValueError:
        raise ValueError(f"Unknown suite: {suite_name}. Valid suites: {[s.value for s in Suite]}")

    # Load custom tasks if path provided
    if custom_path is not None and custom_path.exists():
        with open(custom_path, "r") as f:
            data = json.load(f)
            custom_tasks = [BenchmarkTask(**task) for task in data.get("tasks", [])]
            # Filter to requested suite
            tasks = [t for t in custom_tasks if t.suite == suite]
            if subset_percent < 100:
                tasks = _sample_tasks(tasks, subset_percent=subset_percent, seed=seed)
            return tasks

    # Return built-in tasks for the suite
    return get_tasks(
        suite=suite,
        benchmark=benchmark,
        subset_percent=subset_percent,
        seed=seed,
    )


def _load_janus_tasks() -> list[BenchmarkTask]:
    """Load Janus benchmark tasks from JSON files."""
    tasks: list[BenchmarkTask] = []
    for adapter in list_adapters():
        tasks.extend(adapter.to_tasks(suite=Suite.JANUS_INTELLIGENCE))

    return tasks


def _sample_tasks(
    tasks: list[BenchmarkTask],
    subset_percent: int,
    seed: Optional[int],
) -> list[BenchmarkTask]:
    """Select a deterministic subset of tasks per benchmark."""
    if not tasks:
        return tasks
    if subset_percent <= 0:
        return []
    if subset_percent >= 100:
        return tasks

    by_benchmark: dict[str, list[BenchmarkTask]] = {}
    for task in tasks:
        by_benchmark.setdefault(task.benchmark, []).append(task)

    sampled: list[BenchmarkTask] = []
    for benchmark, group in by_benchmark.items():
        rng = random.Random(f"{seed}:{benchmark}")
        shuffled = list(group)
        rng.shuffle(shuffled)
        take_count = max(1, math.ceil(len(shuffled) * subset_percent / 100))
        sampled.extend(shuffled[:take_count])

    return sorted(sampled, key=lambda t: t.id)
