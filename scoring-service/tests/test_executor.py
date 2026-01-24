import uuid
from datetime import datetime

import pytest
from janus_bench.models import BenchmarkReport, StreamingMetrics, TaskResult, TaskType


@pytest.mark.asyncio
async def test_execute_scoring_run_updates_status(monkeypatch, client):
    from scoring_service.database import ScoringRun, SessionLocal
    from scoring_service.executor import execute_scoring_run

    run_id = uuid.uuid4()

    async with SessionLocal() as session:
        run = ScoringRun(
            id=run_id,
            target_type="url",
            target_url="http://example.com",
            suite="quick",
            status="pending",
            progress_current=0,
        )
        session.add(run)
        await session.commit()

    dummy_result = TaskResult(
        task_id="task-1",
        benchmark="janus_research",
        task_type=TaskType.RESEARCH,
        success=True,
        latency_seconds=1.0,
        quality_score=0.9,
        streaming_metrics=StreamingMetrics(
            ttft_seconds=0.2,
            max_gap_seconds=0.1,
            total_chunks=2,
            keep_alive_count=0,
            total_duration_seconds=1.0,
            avg_tps=4.0,
            peak_tps=5.0,
            min_tps=3.0,
            total_tokens=8,
            continuity_score=0.8,
            continuity_gap_count=0,
            continuity_max_gap_seconds=0.1,
            continuity_coefficient_of_variation=0.1,
        ),
    )

    dummy_report = BenchmarkReport(
        run_id="test",
        suite="janus/intelligence",
        target_url="http://example.com",
        model="deepseek-reasoner",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        composite_score=85.0,
        quality_score=90.0,
        speed_score=80.0,
        cost_score=70.0,
        streaming_score=75.0,
        multimodal_score=60.0,
        total_tasks=1,
        passed_tasks=1,
        failed_tasks=0,
        avg_latency_seconds=1.0,
        p50_latency_seconds=1.0,
        avg_ttft_seconds=0.2,
        max_gap_seconds=0.1,
        total_tokens=8,
        total_cost_usd=0.01,
        results=[dummy_result],
        weights={
            "quality": 40,
            "speed": 20,
            "cost": 15,
            "streaming": 15,
            "multimodal": 10,
        },
    )

    class DummyRunner:
        def __init__(self, settings):
            self.settings = settings

        async def run_suite(self, suite_name, benchmark=None, progress_callback=None):
            if progress_callback:
                progress_callback(1, 1, dummy_result)
            return dummy_report

        async def close(self):
            return None

    monkeypatch.setattr("scoring_service.executor.BenchmarkRunner", DummyRunner)
    monkeypatch.setattr("scoring_service.executor.load_suite", lambda *args, **kwargs: ["task"])

    await execute_scoring_run(run_id)

    async with SessionLocal() as session:
        updated = await session.get(ScoringRun, run_id)
        assert updated.status == "completed"
        assert float(updated.composite_score) == 0.85
        assert float(updated.quality_score) == 0.9
