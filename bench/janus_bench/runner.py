"""Benchmark runner - executes tasks against the Janus Gateway."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from statistics import median
from typing import AsyncGenerator, Optional

import httpx
import structlog

from .config import Settings, get_settings
from .datasets import load_suite
from .models import (
    BenchmarkReport,
    BenchmarkTask,
    StreamingMetrics,
    TaskResult,
    TaskType,
)
from .scorers import compute_composite_score, compute_task_scores

logger = structlog.get_logger()


class BenchmarkRunner:
    """Executes benchmark tasks against a Janus Gateway."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the runner with optional settings override."""
        self.settings = settings or get_settings()
        self.client = httpx.AsyncClient(timeout=self.settings.request_timeout)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def run_task(self, task: BenchmarkTask) -> TaskResult:
        """Run a single benchmark task.

        Args:
            task: The benchmark task to execute

        Returns:
            TaskResult with response data and metrics
        """
        # Build the request
        messages = [{"role": "user", "content": self._build_content(task)}]

        payload = {
            "model": self.settings.model,
            "messages": messages,
            "stream": True,
        }

        start_time = time.perf_counter()
        first_token_time: Optional[float] = None
        last_event_time = start_time
        max_gap = 0.0
        total_chunks = 0
        keep_alive_count = 0
        response_text = ""
        usage_data: dict = {}
        error: Optional[str] = None

        try:
            async with self.client.stream(
                "POST",
                f"{self.settings.target_url}/v1/chat/completions",
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    error = f"HTTP {response.status_code}: {await response.aread()}"
                else:
                    async for line in response.aiter_lines():
                        current_time = time.perf_counter()

                        # Track gaps
                        gap = current_time - last_event_time
                        if gap > max_gap:
                            max_gap = gap
                        last_event_time = current_time

                        # Parse SSE events
                        if line.startswith("data: "):
                            data = line[6:].strip()

                            if data == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data)
                                total_chunks += 1

                                # Track TTFT
                                if first_token_time is None:
                                    first_token_time = current_time

                                # Extract content
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        response_text += content

                                # Extract usage (usually in final chunk)
                                if "usage" in chunk:
                                    usage_data = chunk["usage"]

                            except json.JSONDecodeError:
                                pass

                        elif line.startswith(": "):
                            # Keep-alive comment
                            keep_alive_count += 1

        except httpx.TimeoutException:
            error = "Request timed out"
        except Exception as e:
            error = str(e)

        end_time = time.perf_counter()
        latency = end_time - start_time

        # Build streaming metrics
        ttft = (first_token_time - start_time) if first_token_time else latency
        streaming_metrics = StreamingMetrics(
            ttft_seconds=ttft,
            max_gap_seconds=max_gap,
            total_chunks=total_chunks,
            keep_alive_count=keep_alive_count,
            total_duration_seconds=latency,
        )

        # Create result
        result = TaskResult(
            task_id=task.id,
            task_type=task.type,
            success=error is None and len(response_text) > 0,
            response_text=response_text if response_text else None,
            error=error,
            latency_seconds=latency,
            streaming_metrics=streaming_metrics,
            prompt_tokens=usage_data.get("prompt_tokens"),
            completion_tokens=usage_data.get("completion_tokens"),
            total_tokens=usage_data.get("total_tokens"),
            cost_usd=usage_data.get("cost_usd"),
            sandbox_seconds=usage_data.get("sandbox_seconds"),
        )

        # Compute scores
        result = compute_task_scores(
            result,
            expected_answer=task.expected_answer,
            expected_keywords=task.expected_keywords,
            has_image_input=task.image_url is not None,
        )

        logger.info(
            "task_completed",
            task_id=task.id,
            success=result.success,
            latency=round(latency, 3),
            ttft=round(ttft, 3),
            quality_score=round(result.quality_score, 3),
        )

        return result

    def _build_content(self, task: BenchmarkTask) -> list | str:
        """Build message content from task.

        Args:
            task: Benchmark task

        Returns:
            String or list of content parts for the message
        """
        if task.image_url:
            # Multimodal content with image
            return [
                {"type": "text", "text": task.prompt},
                {"type": "image_url", "image_url": {"url": task.image_url}},
            ]
        return task.prompt

    async def run_suite(
        self,
        suite_name: str,
        progress_callback: Optional[callable] = None,
    ) -> BenchmarkReport:
        """Run all tasks in a benchmark suite.

        Args:
            suite_name: Name of the suite (e.g., "public/dev")
            progress_callback: Optional callback for progress updates

        Returns:
            BenchmarkReport with all results and scores
        """
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        # Load tasks
        tasks = load_suite(suite_name)
        logger.info("suite_loaded", suite=suite_name, task_count=len(tasks))

        # Run all tasks
        results: list[TaskResult] = []
        for i, task in enumerate(tasks):
            # Skip private test stubs
            if task.metadata and task.metadata.get("stub"):
                logger.info("skipping_stub_task", task_id=task.id)
                continue

            result = await self.run_task(task)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(tasks), result)

        completed_at = datetime.now()

        # Compute aggregate scores
        scores = compute_composite_score(
            results,
            weight_quality=self.settings.weight_quality,
            weight_speed=self.settings.weight_speed,
            weight_cost=self.settings.weight_cost,
            weight_streaming=self.settings.weight_streaming,
            weight_multimodal=self.settings.weight_multimodal,
        )

        # Compute aggregate metrics
        latencies = [r.latency_seconds for r in results]
        ttfts = [r.streaming_metrics.ttft_seconds for r in results if r.streaming_metrics]
        max_gaps = [r.streaming_metrics.max_gap_seconds for r in results if r.streaming_metrics]
        total_tokens = sum(r.total_tokens or 0 for r in results)
        total_cost = sum(r.cost_usd or 0 for r in results)

        report = BenchmarkReport(
            run_id=run_id,
            suite=suite_name,
            target_url=self.settings.target_url,
            model=self.settings.model,
            started_at=started_at,
            completed_at=completed_at,
            composite_score=scores["composite_score"],
            quality_score=scores["quality_score"],
            speed_score=scores["speed_score"],
            cost_score=scores["cost_score"],
            streaming_score=scores["streaming_score"],
            multimodal_score=scores["multimodal_score"],
            total_tasks=len(results),
            passed_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success),
            avg_latency_seconds=sum(latencies) / len(latencies) if latencies else 0,
            p50_latency_seconds=median(latencies) if latencies else 0,
            avg_ttft_seconds=sum(ttfts) / len(ttfts) if ttfts else None,
            max_gap_seconds=max(max_gaps) if max_gaps else None,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            results=results,
            weights={
                "quality": self.settings.weight_quality,
                "speed": self.settings.weight_speed,
                "cost": self.settings.weight_cost,
                "streaming": self.settings.weight_streaming,
                "multimodal": self.settings.weight_multimodal,
            },
        )

        logger.info(
            "suite_completed",
            run_id=run_id,
            composite_score=round(scores["composite_score"], 2),
            passed=report.passed_tasks,
            failed=report.failed_tasks,
        )

        return report
