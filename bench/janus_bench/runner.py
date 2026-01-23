"""Benchmark runner - executes tasks against the Janus Gateway."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from statistics import median
from typing import Any, AsyncGenerator, Callable, Optional, cast

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
from .scorers import (
    compute_composite_score,
    compute_task_scores,
    score_quality,
    score_tool_use,
)
from .scorers.research import (
    build_judge_prompt,
    detect_citations,
    detect_search_usage,
    extract_judge_score,
    parse_json_block,
    score_key_facts,
)

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
        task_metadata = dict(task.metadata or {})
        available_tools = task_metadata.get("available_tools") or task_metadata.get("tools")
        if available_tools:
            payload["tools"] = available_tools
            tool_choice = task_metadata.get("tool_choice", "auto")
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        if "temperature" in task_metadata:
            payload["temperature"] = task_metadata["temperature"]

        start_time = time.perf_counter()
        first_token_time: Optional[float] = None
        last_event_time = start_time
        max_gap = 0.0
        total_chunks = 0
        keep_alive_count = 0
        response_text = ""
        usage_data: dict[str, object] = {}
        error: Optional[str] = None
        tool_call_chunks: dict[int, dict[str, object]] = {}

        try:
            async with self.client.stream(
                "POST",
                f"{self.settings.target_url}/v1/chat/completions",
                json=payload,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    error_text = error_body.decode("utf-8", errors="replace")
                    error = f"HTTP {response.status_code}: {error_text}"
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
                                    if "tool_calls" in delta:
                                        for tool_call in delta["tool_calls"]:
                                            index = tool_call.get("index", 0)
                                            entry = tool_call_chunks.setdefault(
                                                index,
                                                {
                                                    "id": None,
                                                    "type": None,
                                                    "function": {
                                                        "name": "",
                                                        "arguments": "",
                                                    },
                                                },
                                            )
                                            if "id" in tool_call:
                                                entry["id"] = tool_call["id"]
                                            if "type" in tool_call:
                                                entry["type"] = tool_call["type"]
                                            if "function" in tool_call:
                                                function = tool_call["function"]
                                                if function.get("name"):
                                                    entry["function"]["name"] = function["name"]
                                                if "arguments" in function and function["arguments"] is not None:
                                                    entry["function"]["arguments"] += function["arguments"]
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

        prompt_tokens = cast(Optional[int], usage_data.get("prompt_tokens"))
        completion_tokens = cast(Optional[int], usage_data.get("completion_tokens"))
        total_tokens = cast(Optional[int], usage_data.get("total_tokens"))
        cost_usd = cast(Optional[float], usage_data.get("cost_usd"))
        sandbox_seconds = cast(Optional[float], usage_data.get("sandbox_seconds"))

        tool_calls: list[dict[str, object]] = []
        for index in sorted(tool_call_chunks):
            entry = tool_call_chunks[index]
            function = entry.get("function") or {}
            name = function.get("name") if isinstance(function, dict) else None
            args_raw = ""
            if isinstance(function, dict):
                args_raw = cast(str, function.get("arguments") or "")
            arguments: dict[str, object] = {}
            if args_raw:
                try:
                    arguments = json.loads(args_raw)
                except json.JSONDecodeError:
                    arguments = {}
            tool_call_payload: dict[str, object] = {
                "function": name,
                "arguments": arguments,
            }
            if args_raw:
                tool_call_payload["arguments_raw"] = args_raw
            if entry.get("id"):
                tool_call_payload["id"] = entry["id"]
            if entry.get("type"):
                tool_call_payload["type"] = entry["type"]
            tool_calls.append(tool_call_payload)

        # Create result
        result = TaskResult(
            task_id=task.id,
            benchmark=task.benchmark,
            task_type=task.type,
            success=error is None and len(response_text) > 0,
            response_text=response_text if response_text else None,
            error=error,
            latency_seconds=latency,
            streaming_metrics=streaming_metrics,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            sandbox_seconds=sandbox_seconds,
        )

        if tool_calls or task_metadata:
            task_metadata = dict(task_metadata)
            if tool_calls:
                task_metadata["tool_calls"] = tool_calls
            result.metadata = task_metadata or None

        if task.benchmark == "janus_research" and error is None and response_text:
            (
                quality_score,
                research_metadata,
                judge_score,
                judge_output,
            ) = await self._score_research_task(task, response_text)
            result.quality_score = quality_score
            result.metadata = research_metadata
            result.judge_score = judge_score
            result.judge_output = judge_output
        elif task.type == TaskType.TOOL_USE:
            tool_score, reasoning = score_tool_use(
                response_text,
                tool_calls,
                task_metadata,
            )
            task_metadata = dict(task_metadata or {})
            task_metadata["quality_override"] = True
            result.metadata = task_metadata
            result.judge_output = {
                "reasoning": reasoning,
                "tool_calls": tool_calls,
            }
            result.quality_score = tool_score

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

    def _build_content(self, task: BenchmarkTask) -> list[dict[str, object]] | str:
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

    def _judge_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.settings.judge_api_key:
            headers["Authorization"] = f"Bearer {self.settings.judge_api_key}"
        return headers

    def _judge_url(self) -> Optional[str]:
        if not self.settings.judge_url:
            return None
        base = self.settings.judge_url.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    async def _run_judge_prompt(
        self,
        prompt: str,
    ) -> tuple[Optional[float], Optional[dict[str, Any]]]:
        judge_url = self._judge_url()
        if not judge_url:
            return None, None

        payload = {
            "model": self.settings.judge_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self.client.post(
                judge_url,
                json=payload,
                headers=self._judge_headers(),
                timeout=self.settings.judge_timeout,
            )
        except Exception as exc:
            return None, {"error": str(exc)}

        if response.status_code != 200:
            return None, {"error": f"HTTP {response.status_code}: {response.text}"}

        try:
            data = response.json()
        except ValueError as exc:
            return None, {"error": f"Invalid JSON response: {exc}"}

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = parse_json_block(content)
        if parsed is None:
            return None, {"error": "Invalid judge output", "raw": content}

        return extract_judge_score(parsed), parsed

    async def _score_research_task(
        self,
        task: BenchmarkTask,
        response_text: str,
    ) -> tuple[float, dict[str, Any], Optional[float], Optional[dict[str, Any]]]:
        task_metadata = task.metadata or {}
        evaluation = task_metadata.get("evaluation") or {}
        research_type = task_metadata.get("research_task_type") or task_metadata.get("task_type") or "research"
        query = task_metadata.get("query") or task_metadata.get("claim") or task.prompt

        expected_facts: list[str] = []
        for key in (
            "expected_facts",
            "expected_topics",
            "required_aspects",
            "required_elements",
            "required_concepts",
        ):
            value = task_metadata.get(key) or evaluation.get(key)
            if isinstance(value, list):
                expected_facts.extend(str(item) for item in value if item)

        key_fact_score = (
            score_key_facts(response_text, expected_facts) if expected_facts else None
        )
        search_used = detect_search_usage(response_text)
        citation_used = detect_citations(response_text)

        judge_score = None
        judge_output = None
        if self.settings.judge_url:
            judge_prompt = build_judge_prompt(research_type, query, evaluation, response_text)
            judge_score, judge_output = await self._run_judge_prompt(judge_prompt)

        if judge_score is not None and key_fact_score is not None:
            quality_score = (judge_score * 0.7) + (key_fact_score * 0.3)
        elif judge_score is not None:
            quality_score = judge_score
        elif key_fact_score is not None:
            quality_score = key_fact_score
        else:
            quality_score = score_quality(response_text)

        quality_score = max(0.0, min(1.0, quality_score))

        result_metadata = {
            "research_task_type": research_type,
            "search_used": search_used,
            "citation_used": citation_used,
            "key_fact_score": key_fact_score,
            "quality_source": "judge" if judge_score is not None else "heuristic",
            "quality_override": True,
        }

        return quality_score, result_metadata, judge_score, judge_output

    async def run_suite(
        self,
        suite_name: str,
        benchmark: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, TaskResult], None]] = None,
    ) -> BenchmarkReport:
        """Run all tasks in a benchmark suite.

        Args:
            suite_name: Name of the suite (e.g., "public/dev")
            benchmark: Optional benchmark name to filter tasks
            progress_callback: Optional callback for progress updates

        Returns:
            BenchmarkReport with all results and scores
        """
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        # Load tasks
        tasks = load_suite(
            suite_name,
            benchmark=benchmark,
            subset_percent=self.settings.subset_percent,
            seed=self.settings.seed,
        )
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
        benchmark_scores = cast(dict[str, float], scores.get("benchmark_scores", {}))
        benchmark_metrics = cast(
            dict[str, dict[str, object]],
            scores.get("benchmark_metrics", {}),
        )

        composite_score = cast(float, scores["composite_score"])
        quality_score = cast(float, scores["quality_score"])
        speed_score = cast(float, scores["speed_score"])
        cost_score = cast(float, scores["cost_score"])
        streaming_score = cast(float, scores["streaming_score"])
        multimodal_score = cast(float, scores["multimodal_score"])

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
            composite_score=composite_score,
            quality_score=quality_score,
            speed_score=speed_score,
            cost_score=cost_score,
            streaming_score=streaming_score,
            multimodal_score=multimodal_score,
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
            benchmark_scores=benchmark_scores,
            benchmark_metrics=benchmark_metrics,
        )

        logger.info(
            "suite_completed",
            run_id=run_id,
            composite_score=round(composite_score, 2),
            passed=report.passed_tasks,
            failed=report.failed_tasks,
        )

        return report
