"""Benchmark adapter base classes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import BenchmarkName, BenchmarkTask, Suite, TaskType


@dataclass(frozen=True)
class BenchmarkMetadata:
    """Metadata for a benchmark adapter."""

    name: str
    display_name: str
    category: str
    description: str
    total_items: int
    default_selected: bool = True


class BenchmarkAdapter:
    """Base class for Janus benchmark adapters."""

    name: BenchmarkName
    display_name: str
    description: str
    category: str = "Janus Intelligence"
    data_file: str
    task_type: TaskType
    subtask_metadata_key: str | None = None

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] | None = None

    def _data_path(self) -> Path:
        return (
            Path(__file__).resolve().parent.parent
            / "datasets"
            / "data"
            / "janus"
            / self.data_file
        )

    def get_items(self) -> list[dict[str, Any]]:
        if self._items is None:
            with open(self._data_path(), "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self._items = payload.get("items", [])
        return self._items

    def get_total_items(self) -> int:
        return len(self.get_items())

    def to_tasks(
        self,
        suite: Suite | None = None,
        default_suite: Suite | None = None,
    ) -> list[BenchmarkTask]:
        tasks: list[BenchmarkTask] = []
        resolved_default = suite or default_suite
        for item in self.get_items():
            if resolved_default is None:
                suite_value = item.get("suite", Suite.PUBLIC_DEV.value)
                resolved_suite = Suite(suite_value)
            else:
                resolved_suite = resolved_default

            raw_task_type = item.get("task_type", self.task_type.value)
            metadata = dict(item.get("metadata") or {})
            for key, value in item.items():
                if key in {
                    "id",
                    "suite",
                    "task_type",
                    "prompt",
                    "expected_answer",
                    "expected_keywords",
                    "image_url",
                    "metadata",
                }:
                    continue
                metadata.setdefault(key, value)

            if raw_task_type in TaskType._value2member_map_:
                resolved_task_type = TaskType(raw_task_type)
            else:
                subtask_key = self.subtask_metadata_key or "task_type"
                metadata.setdefault(subtask_key, raw_task_type)
                resolved_task_type = self.task_type

            prompt = item.get("prompt") or item.get("query") or item.get("claim")
            if not prompt:
                raise ValueError(f"Missing prompt for benchmark item {item.get('id')}")

            tasks.append(
                BenchmarkTask(
                    id=item["id"],
                    suite=resolved_suite,
                    type=resolved_task_type,
                    prompt=prompt,
                    expected_answer=item.get("expected_answer"),
                    expected_keywords=item.get("expected_keywords"),
                    image_url=item.get("image_url"),
                    metadata=metadata or None,
                    benchmark=self.name.value,
                )
            )
        return tasks

    def get_metadata(self) -> BenchmarkMetadata:
        return BenchmarkMetadata(
            name=self.name.value,
            display_name=self.display_name,
            category=self.category,
            description=self.description,
            total_items=self.get_total_items(),
            default_selected=True,
        )
