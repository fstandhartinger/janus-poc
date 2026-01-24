import uuid

import pytest
from janus_bench.models import StreamingMetrics, TaskResult, TaskType


@pytest.mark.asyncio
async def test_create_and_list_runs(client):
    payload = {
        "target_type": "url",
        "target_url": "http://example.com",
        "suite": "quick",
        "model": "deepseek-reasoner",
        "subset_percent": 100,
    }
    response = await client.post("/api/runs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["target_type"] == "url"

    list_response = await client.get("/api/runs")
    assert list_response.status_code == 200
    runs = list_response.json()
    assert any(run["id"] == data["id"] for run in runs)


@pytest.mark.asyncio
async def test_run_summary(client):
    payload = {
        "target_type": "url",
        "target_url": "http://example.com",
        "suite": "quick",
    }
    response = await client.post("/api/runs", json=payload)
    run_id = response.json()["id"]

    from scoring_service.database import SessionLocal
    from scoring_service.repository import store_task_result, update_run_completed

    async with SessionLocal() as session:
        await update_run_completed(
            session,
            uuid.UUID(run_id),
            composite_score=0.85,
            quality_score=0.9,
            speed_score=0.8,
            cost_score=0.75,
            streaming_score=0.7,
            multimodal_score=0.6,
            completed_at=None,
        )

    result = TaskResult(
        task_id="task-1",
        benchmark="janus_research",
        task_type=TaskType.RESEARCH,
        success=True,
        latency_seconds=1.2,
        quality_score=0.9,
        streaming_metrics=StreamingMetrics(
            ttft_seconds=0.4,
            max_gap_seconds=0.2,
            total_chunks=4,
            keep_alive_count=0,
            total_duration_seconds=1.2,
            avg_tps=5.0,
            peak_tps=6.0,
            min_tps=4.0,
            total_tokens=10,
            continuity_score=0.8,
            continuity_gap_count=0,
            continuity_max_gap_seconds=0.2,
            continuity_coefficient_of_variation=0.1,
        ),
    )

    async with SessionLocal() as session:
        await store_task_result(session, uuid.UUID(run_id), result)

    summary_response = await client.get(f"/api/runs/{run_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["run_id"] == run_id
    assert summary["composite_score"] == 0.85
    assert "janus_research" in summary["by_benchmark"]


@pytest.mark.asyncio
async def test_leaderboard(client):
    from scoring_service.database import Competitor, SessionLocal

    async with SessionLocal() as session:
        competitor = Competitor(
            name="Test Competitor",
            container_image="repo/test:latest",
            verified=True,
            is_baseline=False,
        )
        session.add(competitor)
        await session.commit()
        await session.refresh(competitor)

    payload = {
        "target_type": "competitor_id",
        "suite": "quick",
        "competitor_id": str(competitor.id),
    }
    response = await client.post("/api/runs", json=payload)
    run_id = uuid.UUID(response.json()["id"])

    from scoring_service.repository import update_competitor_best_score, update_run_completed

    async with SessionLocal() as session:
        await update_run_completed(
            session,
            run_id,
            composite_score=0.9,
            quality_score=0.9,
            speed_score=0.9,
            cost_score=0.9,
            streaming_score=0.9,
            multimodal_score=0.9,
            completed_at=None,
        )
        await update_competitor_best_score(session, competitor.id, 0.9, run_id)

    leaderboard_response = await client.get("/api/leaderboard")
    assert leaderboard_response.status_code == 200
    leaderboard = leaderboard_response.json()
    assert leaderboard
    assert leaderboard[0]["competitor"]["name"] == "Test Competitor"


@pytest.mark.asyncio
async def test_stream_progress(client):
    payload = {
        "target_type": "url",
        "target_url": "http://example.com",
        "suite": "quick",
    }
    response = await client.post("/api/runs", json=payload)
    run_id = response.json()["id"]

    from scoring_service.main import stream_run_progress

    stream_response = await stream_run_progress(uuid.UUID(run_id))
    assert stream_response.media_type == "text/event-stream"
    assert stream_response.headers["Cache-Control"] == "no-cache"
