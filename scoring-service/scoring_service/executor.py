import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from janus_bench.config import Settings
from janus_bench.datasets import load_suite
from janus_bench.runner import BenchmarkRunner
from janus_bench.models import TaskResult

from scoring_service.database import SessionLocal
from scoring_service.repository import (
    get_competitor,
    get_run,
    store_task_result,
    update_competitor_best_score,
    update_run_completed,
    update_run_progress,
    update_run_status,
)
from scoring_service.sandy import cleanup_sandbox, health_check_sandbox, start_container_in_sandbox
from scoring_service.settings import get_settings


settings = get_settings()
_run_queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
_workers: list[asyncio.Task] = []
_shutdown_event = asyncio.Event()


SUITE_MAP: dict[str, Tuple[str, Optional[str]]] = {
    "quick": ("janus/intelligence", None),
    "full": ("janus/intelligence", None),
    "research": ("janus/intelligence", "janus_research"),
    "tool_use": ("janus/intelligence", "janus_tool_use"),
    "multimodal": ("janus/intelligence", "janus_multimodal"),
    "streaming": ("janus/intelligence", "janus_streaming"),
    "cost": ("janus/intelligence", "janus_cost"),
}


async def enqueue_run(run_id: uuid.UUID) -> None:
    await _run_queue.put(run_id)


async def start_workers() -> None:
    if _workers:
        return
    for _ in range(settings.max_concurrent_runs):
        _workers.append(asyncio.create_task(_worker()))


async def stop_workers() -> None:
    _shutdown_event.set()
    for task in _workers:
        task.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)
    _workers.clear()
    _shutdown_event.clear()


async def _worker() -> None:
    while not _shutdown_event.is_set():
        try:
            run_id = await asyncio.wait_for(_run_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue

        try:
            await execute_scoring_run(run_id)
        except Exception:
            pass
        finally:
            _run_queue.task_done()


def _resolve_suite(suite: str) -> Tuple[str, Optional[str]]:
    if suite not in SUITE_MAP:
        raise ValueError(f"Unknown suite: {suite}")
    return SUITE_MAP[suite]


async def _get_run(run_id: uuid.UUID):
    async with SessionLocal() as session:
        return await get_run(session, run_id)


async def _update_run_status(run_id: uuid.UUID, status: str, **kwargs) -> None:
    async with SessionLocal() as session:
        await update_run_status(session, run_id, status, **kwargs)


async def _update_run_progress(run_id: uuid.UUID, current: int, total: Optional[int]) -> None:
    async with SessionLocal() as session:
        await update_run_progress(session, run_id, current, total)


async def _store_task_result(run_id: uuid.UUID, result: TaskResult) -> None:
    async with SessionLocal() as session:
        await store_task_result(session, run_id, result)


async def _update_run_completed(run_id: uuid.UUID, **kwargs) -> None:
    async with SessionLocal() as session:
        await update_run_completed(session, run_id, **kwargs)


async def _update_competitor_best(competitor_id: uuid.UUID, composite_score: float, run_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        await update_competitor_best_score(session, competitor_id, composite_score, run_id)


async def _get_competitor(competitor_id: uuid.UUID):
    async with SessionLocal() as session:
        return await get_competitor(session, competitor_id)


async def execute_scoring_run(run_id: uuid.UUID) -> None:
    run = await _get_run(run_id)
    if not run or run.status in {"completed", "failed", "cancelled"}:
        return

    runner: Optional[BenchmarkRunner] = None
    target_url: Optional[str] = None

    try:
        await _update_run_status(run_id, "running", started_at=datetime.now(tz=timezone.utc))

        if run.target_type == "url":
            if not run.target_url:
                raise ValueError("Target URL missing")
            target_url = run.target_url
        elif run.target_type == "container":
            if not run.container_image:
                raise ValueError("Container image missing")
            target_url = await start_container_in_sandbox(run.container_image)
        elif run.target_type == "competitor_id":
            competitor = await _get_competitor(run.competitor_id)
            if not competitor:
                raise ValueError("Competitor not found")
            target_url = await start_container_in_sandbox(competitor.container_image)
        else:
            raise ValueError(f"Unknown target_type: {run.target_type}")

        if not target_url:
            raise ValueError("Target URL not available")

        if run.target_type in {"container", "competitor_id"}:
            ready = await health_check_sandbox(target_url)
            if not ready:
                raise RuntimeError("Sandbox health check failed")

        suite_name, benchmark = _resolve_suite(run.suite)
        tasks = load_suite(suite_name, benchmark=benchmark, subset_percent=run.subset_percent, seed=42)
        await _update_run_progress(run_id, 0, len(tasks))

        bench_settings = Settings(
            target_url=target_url,
            model=run.model or "deepseek-reasoner",
            subset_percent=run.subset_percent,
            seed=42,
            judge_url=settings.judge_url,
            judge_api_key=settings.judge_api_key,
            judge_model=settings.judge_model,
        )
        runner = BenchmarkRunner(bench_settings)

        def on_progress(current: int, total: int, result: TaskResult) -> None:
            asyncio.create_task(_update_run_progress(run_id, current, total))
            asyncio.create_task(_store_task_result(run_id, result))

        report = await runner.run_suite(
            suite_name,
            benchmark=benchmark,
            progress_callback=on_progress,
        )

        latest_run = await _get_run(run_id)
        if latest_run and latest_run.status == "cancelled":
            await _update_run_status(
                run_id, "cancelled", completed_at=datetime.now(tz=timezone.utc)
            )
            return

        await _update_run_completed(
            run_id,
            composite_score=report.composite_score / 100,
            quality_score=report.quality_score / 100,
            speed_score=report.speed_score / 100,
            cost_score=report.cost_score / 100,
            streaming_score=report.streaming_score / 100,
            multimodal_score=report.multimodal_score / 100,
            completed_at=datetime.now(tz=timezone.utc),
        )

        if run.competitor_id:
            await _update_competitor_best(run.competitor_id, report.composite_score / 100, run_id)

    except Exception as exc:
        latest_run = await _get_run(run_id)
        if not latest_run or latest_run.status != "cancelled":
            await _update_run_status(run_id, "failed", error=str(exc))
    finally:
        if runner:
            await runner.close()
        if target_url and run.target_type in {"container", "competitor_id"}:
            await cleanup_sandbox(target_url)
