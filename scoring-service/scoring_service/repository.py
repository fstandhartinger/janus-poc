import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from janus_bench.models import TaskResult as BenchTaskResult

from scoring_service.database import (
    ArenaVote,
    Competitor,
    ScoringRun,
    TaskResult as TaskResultRow,
)
from scoring_service.models import ArenaVoteRequest, CreateRunRequest
from scoring_service.utils import redact_pii


async def create_run(session: AsyncSession, request: CreateRunRequest) -> ScoringRun:
    run = ScoringRun(
        target_type=request.target_type,
        target_url=request.target_url,
        container_image=request.container_image,
        competitor_id=request.competitor_id,
        suite=request.suite,
        model=request.model,
        subset_percent=request.subset_percent,
        status="pending",
        progress_current=0,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def list_runs(
    session: AsyncSession,
    limit: int,
    offset: int,
    status: Optional[str],
    competitor_id: Optional[uuid.UUID],
) -> list[ScoringRun]:
    query = select(ScoringRun).order_by(ScoringRun.created_at.desc()).limit(limit).offset(offset)
    if status:
        query = query.where(ScoringRun.status == status)
    if competitor_id:
        query = query.where(ScoringRun.competitor_id == competitor_id)
    result = await session.execute(query)
    return list(result.scalars())


async def get_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    include_results: bool = False,
) -> Optional[ScoringRun]:
    query = select(ScoringRun).where(ScoringRun.id == run_id)
    if include_results:
        query = query.options(selectinload(ScoringRun.results))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def update_run_status(
    session: AsyncSession,
    run_id: uuid.UUID,
    status: str,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    error: Optional[str] = None,
) -> None:
    run = await get_run(session, run_id)
    if not run:
        return
    run.status = status
    if started_at:
        run.started_at = started_at
    if completed_at:
        run.completed_at = completed_at
    if error:
        run.error = error
    await session.commit()


async def update_run_progress(
    session: AsyncSession,
    run_id: uuid.UUID,
    current: int,
    total: Optional[int],
) -> None:
    run = await get_run(session, run_id)
    if not run:
        return
    run.progress_current = current
    if total is not None:
        run.progress_total = total
    await session.commit()


async def update_run_completed(
    session: AsyncSession,
    run_id: uuid.UUID,
    composite_score: Optional[float],
    quality_score: Optional[float],
    speed_score: Optional[float],
    cost_score: Optional[float],
    streaming_score: Optional[float],
    multimodal_score: Optional[float],
    completed_at: Optional[datetime],
) -> None:
    run = await get_run(session, run_id)
    if not run:
        return
    run.status = "completed"
    run.composite_score = composite_score
    run.quality_score = quality_score
    run.speed_score = speed_score
    run.cost_score = cost_score
    run.streaming_score = streaming_score
    run.multimodal_score = multimodal_score
    run.completed_at = completed_at
    await session.commit()


async def cancel_run(session: AsyncSession, run_id: uuid.UUID) -> None:
    run = await get_run(session, run_id)
    if not run:
        return
    run.status = "cancelled"
    await session.commit()


async def store_task_result(
    session: AsyncSession, run_id: uuid.UUID, result: BenchTaskResult
) -> None:
    response_text = redact_pii(result.response_text)
    error = redact_pii(result.error)

    streaming_metrics = None
    continuity_score = None
    max_gap_seconds = None
    ttft_seconds = None
    avg_tps = None
    if result.streaming_metrics:
        streaming_metrics = result.streaming_metrics.model_dump()
        continuity_score = result.streaming_metrics.continuity_score
        max_gap_seconds = result.streaming_metrics.max_gap_seconds
        ttft_seconds = result.streaming_metrics.ttft_seconds
        avg_tps = result.streaming_metrics.avg_tps

    task_result = TaskResultRow(
        run_id=run_id,
        task_id=result.task_id,
        benchmark=result.benchmark,
        task_type=result.task_type.value if result.task_type else None,
        success=result.success,
        response_text=response_text,
        error=error,
        quality_score=result.quality_score,
        latency_seconds=result.latency_seconds,
        ttft_seconds=ttft_seconds,
        avg_tps=avg_tps,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        cost_usd=result.cost_usd,
        continuity_score=continuity_score,
        max_gap_seconds=max_gap_seconds,
        streaming_metrics=streaming_metrics,
        metadata_=result.metadata,
    )
    session.add(task_result)
    await session.commit()


async def list_results(
    session: AsyncSession,
    run_id: uuid.UUID,
    benchmark: Optional[str],
    success_only: bool,
) -> list[TaskResultRow]:
    query = select(TaskResultRow).where(TaskResultRow.run_id == run_id)
    if benchmark:
        query = query.where(TaskResultRow.benchmark == benchmark)
    if success_only:
        query = query.where(TaskResultRow.success.is_(True))
    result = await session.execute(query.order_by(TaskResultRow.created_at.asc()))
    return list(result.scalars())


async def compute_run_summary(session: AsyncSession, run_id: uuid.UUID) -> Optional[dict]:
    run = await get_run(session, run_id)
    if not run:
        return None
    result = await session.execute(select(TaskResultRow).where(TaskResultRow.run_id == run_id))
    results = list(result.scalars())

    by_benchmark: dict[str, dict[str, float]] = {}
    benchmark_groups: dict[str, list[TaskResultRow]] = defaultdict(list)
    for entry in results:
        benchmark_groups[entry.benchmark].append(entry)

    for benchmark, entries in benchmark_groups.items():
        passed = sum(1 for entry in entries if entry.success)
        failed = len(entries) - passed
        scores = [entry.quality_score for entry in entries if entry.quality_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        by_benchmark[benchmark] = {
            "score": float(avg_score),
            "passed": passed,
            "failed": failed,
        }

    latencies = [entry.latency_seconds for entry in results if entry.latency_seconds is not None]
    ttfts = [entry.ttft_seconds for entry in results if entry.ttft_seconds is not None]
    total_tokens = sum(entry.total_tokens or 0 for entry in results)
    total_cost = sum(float(entry.cost_usd or 0) for entry in results)

    metrics = {
        "avg_latency_seconds": float(sum(latencies) / len(latencies)) if latencies else 0.0,
        "avg_ttft_seconds": float(sum(ttfts) / len(ttfts)) if ttfts else 0.0,
        "total_tokens": float(total_tokens),
        "total_cost_usd": float(total_cost),
    }

    scores = {
        "quality": float(run.quality_score or 0),
        "speed": float(run.speed_score or 0),
        "cost": float(run.cost_score or 0),
        "streaming": float(run.streaming_score or 0),
        "multimodal": float(run.multimodal_score or 0),
    }

    return {
        "run_id": run.id,
        "composite_score": float(run.composite_score or 0),
        "scores": scores,
        "by_benchmark": by_benchmark,
        "metrics": metrics,
    }


async def list_competitors(
    session: AsyncSession,
    include_baselines: bool,
    verified_only: bool,
) -> list[Competitor]:
    query = select(Competitor)
    if not include_baselines:
        query = query.where(Competitor.is_baseline.is_(False))
    if verified_only:
        query = query.where(Competitor.verified.is_(True))
    result = await session.execute(query.order_by(Competitor.created_at.asc()))
    return list(result.scalars())


async def get_competitor(session: AsyncSession, competitor_id: uuid.UUID) -> Optional[Competitor]:
    result = await session.execute(select(Competitor).where(Competitor.id == competitor_id))
    return result.scalar_one_or_none()


async def update_competitor_best_score(
    session: AsyncSession,
    competitor_id: uuid.UUID,
    composite_score: float,
    run_id: uuid.UUID,
) -> None:
    competitor = await get_competitor(session, competitor_id)
    if not competitor:
        return
    if competitor.best_composite_score is None or composite_score > competitor.best_composite_score:
        competitor.best_composite_score = composite_score
        competitor.best_run_id = run_id
        await session.commit()


async def get_leaderboard(
    session: AsyncSession,
    limit: int,
    verified_only: bool,
) -> list[tuple[Competitor, Optional[ScoringRun]]]:
    query = select(Competitor)
    if verified_only:
        query = query.where(Competitor.verified.is_(True))
    query = query.order_by(Competitor.best_composite_score.desc().nullslast()).limit(limit)
    competitors = list((await session.execute(query)).scalars())

    leaderboard: list[tuple[Competitor, Optional[ScoringRun]]] = []
    for competitor in competitors:
        best_run = None
        if competitor.best_run_id:
            best_run = await get_run(session, competitor.best_run_id)
        leaderboard.append((competitor, best_run))
    return leaderboard


async def store_arena_vote(session: AsyncSession, request: ArenaVoteRequest) -> ArenaVote:
    vote = ArenaVote(
        prompt_id=request.prompt_id,
        prompt_hash=request.prompt_hash,
        model_a=request.model_a,
        model_b=request.model_b,
        winner=request.winner,
        user_id=request.user_id,
    )
    session.add(vote)
    await session.commit()
    await session.refresh(vote)
    return vote


async def list_arena_votes(session: AsyncSession) -> list[ArenaVote]:
    result = await session.execute(select(ArenaVote).order_by(ArenaVote.created_at.asc()))
    return list(result.scalars())
