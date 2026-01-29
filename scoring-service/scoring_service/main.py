import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from scoring_service.database import SessionLocal, close_db, get_session, init_db
from scoring_service.arena_elo import compute_leaderboard
from scoring_service.executor import enqueue_run, start_workers, stop_workers
from scoring_service.models import (
    ArenaLeaderboardEntry,
    ArenaVoteRequest,
    ArenaVoteResponse,
    CompetitorResponse,
    CreateRunRequest,
    LeaderboardEntry,
    RunSummaryResponse,
    ScoringRunDetailResponse,
    ScoringRunResponse,
    TaskResultResponse,
)
from scoring_service.repository import (
    cancel_run,
    compute_run_summary,
    create_run,
    get_leaderboard,
    get_run,
    list_competitors,
    list_arena_votes,
    list_results,
    list_runs,
    store_arena_vote,
)
from scoring_service.settings import get_settings
from scoring_service.utils import is_valid_container_image


settings = get_settings()
app = FastAPI(title="Janus Scoring Service", version="1.0.0")
_rate_limit: dict[str, Deque[float]] = defaultdict(deque)


@app.on_event("startup")
async def startup() -> None:
    if settings.init_db:
        await init_db()
    await start_workers()


@app.on_event("shutdown")
async def shutdown() -> None:
    await stop_workers()
    await close_db()


def _check_rate_limit(client_id: str) -> None:
    window = settings.run_rate_window_seconds
    limit = settings.run_rate_limit
    now = time.monotonic()
    history = _rate_limit[client_id]
    while history and now - history[0] > window:
        history.popleft()
    if len(history) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    history.append(now)


async def _get_run_or_404(session: AsyncSession, run_id: uuid.UUID, include_results: bool = False):
    run = await get_run(session, run_id, include_results=include_results)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/runs", response_model=ScoringRunResponse)
async def create_scoring_run(
    request: CreateRunRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> ScoringRunResponse:
    client_host = http_request.client.host if http_request.client else "unknown"
    _check_rate_limit(client_host)

    if request.target_type == "container" and request.container_image:
        if not is_valid_container_image(request.container_image):
            raise HTTPException(status_code=400, detail="Invalid container image")

    created = await create_run(session, request)
    await enqueue_run(created.id)
    return ScoringRunResponse.model_validate(created)


@app.get("/api/runs", response_model=list[ScoringRunResponse])
async def list_scoring_runs(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    competitor_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_session),
) -> list[ScoringRunResponse]:
    runs = await list_runs(session, limit, offset, status, competitor_id)
    return [ScoringRunResponse.model_validate(run) for run in runs]


@app.get("/api/runs/{run_id}", response_model=ScoringRunDetailResponse)
async def get_scoring_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ScoringRunDetailResponse:
    run = await _get_run_or_404(session, run_id, include_results=True)
    results = [TaskResultResponse.model_validate(result) for result in run.results]
    base = ScoringRunResponse.model_validate(run).model_dump()
    return ScoringRunDetailResponse.model_validate({**base, "results": results})


@app.get("/api/runs/{run_id}/stream")
async def stream_run_progress(run_id: uuid.UUID) -> StreamingResponse:
    async def event_stream():
        while True:
            async with SessionLocal() as session:
                run = await get_run(session, run_id)
                if not run:
                    yield "event: failed\ndata: {\"error\": \"Run not found\"}\n\n"
                    break

                if run.status == "completed":
                    payload = ScoringRunResponse.model_validate(run).model_dump_json()
                    yield f"event: completed\ndata: {payload}\n\n"
                    break
                if run.status == "failed":
                    error_payload = json.dumps({"error": run.error or "Run failed"})
                    yield f"event: failed\ndata: {error_payload}\n\n"
                    break
                if run.status == "cancelled":
                    error_payload = json.dumps({"error": "Run cancelled"})
                    yield f"event: failed\ndata: {error_payload}\n\n"
                    break

                progress = {
                    "current": run.progress_current,
                    "total": run.progress_total,
                    "status": run.status,
                }
                yield f"event: progress\ndata: {json.dumps(progress)}\n\n"

            await asyncio.sleep(settings.sse_poll_interval)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.delete("/api/runs/{run_id}")
async def cancel_scoring_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _get_run_or_404(session, run_id)
    await cancel_run(session, run_id)
    return {"status": "cancelled"}


@app.get("/api/runs/{run_id}/results", response_model=list[TaskResultResponse])
async def get_run_results(
    run_id: uuid.UUID,
    benchmark: Optional[str] = None,
    success_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[TaskResultResponse]:
    await _get_run_or_404(session, run_id)
    results = await list_results(session, run_id, benchmark, success_only)
    return [TaskResultResponse.model_validate(result) for result in results]


@app.get("/api/runs/{run_id}/summary", response_model=RunSummaryResponse)
async def get_run_summary(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> RunSummaryResponse:
    summary = await compute_run_summary(session, run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunSummaryResponse(**summary)


@app.get("/api/competitors", response_model=list[CompetitorResponse])
async def list_competitors_endpoint(
    include_baselines: bool = True,
    verified_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[CompetitorResponse]:
    competitors = await list_competitors(session, include_baselines, verified_only)
    return [CompetitorResponse.model_validate(competitor) for competitor in competitors]


@app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard_endpoint(
    limit: int = 50,
    verified_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[LeaderboardEntry]:
    leaderboard = await get_leaderboard(session, limit, verified_only)

    entries: list[LeaderboardEntry] = []
    for rank, (competitor, run) in enumerate(leaderboard, start=1):
        scores: dict[str, float] = {}
        if run:
            scores = {
                "composite": float(run.composite_score or 0),
                "quality": float(run.quality_score or 0),
                "speed": float(run.speed_score or 0),
                "cost": float(run.cost_score or 0),
                "streaming": float(run.streaming_score or 0),
                "multimodal": float(run.multimodal_score or 0),
            }
        entry = LeaderboardEntry(
            rank=rank,
            competitor=CompetitorResponse.model_validate(competitor),
            best_run_id=competitor.best_run_id,
            scores=scores,
        )
        entries.append(entry)

    return entries


@app.post("/api/arena/vote", response_model=ArenaVoteResponse)
async def submit_arena_vote(
    request: ArenaVoteRequest,
    session: AsyncSession = Depends(get_session),
) -> ArenaVoteResponse:
    try:
        vote = await store_arena_vote(session, request)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Vote already recorded")
    return ArenaVoteResponse(id=vote.id, status="recorded")


@app.get("/api/arena/leaderboard", response_model=list[ArenaLeaderboardEntry])
async def get_arena_leaderboard(
    session: AsyncSession = Depends(get_session),
) -> list[ArenaLeaderboardEntry]:
    votes = await list_arena_votes(session)
    leaderboard = compute_leaderboard(
        [{"model_a": vote.model_a, "model_b": vote.model_b, "winner": vote.winner} for vote in votes]
    )
    return [ArenaLeaderboardEntry(**entry) for entry in leaderboard]


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "janus-scoring"}
