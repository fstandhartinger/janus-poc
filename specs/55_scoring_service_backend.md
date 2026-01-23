# Spec 55: Scoring Service Backend

## Status: DRAFT

## Context / Why

The Janus competition needs a dedicated scoring service that:
1. Runs the janus-bench benchmarks against competitor containers
2. Stores scoring runs and results in a database
3. Exposes an API for the frontend to trigger runs and view results
4. Integrates with Sandy sandboxes for container execution
5. Deploys to Render as a standalone service

Currently, chutes-bench-runner exists separately. This scoring service is Janus-specific and integrates directly with the Janus ecosystem.

## Goals

- Create a FastAPI backend service for scoring
- Integrate with the janus-bench library for evaluation
- Store runs and results in Neon PostgreSQL
- Deploy to Render as a new service
- Support concurrent scoring runs with job queue
- Provide real-time progress updates via SSE/WebSocket

## Non-Goals

- Replacing chutes-bench-runner (complementary service)
- Implementing new benchmark types (uses existing janus-bench)
- On-chain verification (future phase)

## Functional Requirements

### FR-1: Database Schema (Neon PostgreSQL)

```sql
-- Scoring runs table
CREATE TABLE scoring_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Target
    target_type VARCHAR(50) NOT NULL, -- 'url', 'container', 'competitor_id'
    target_url TEXT,
    container_image TEXT,
    competitor_id UUID REFERENCES competitors(id),

    -- Configuration
    suite VARCHAR(50) NOT NULL DEFAULT 'quick', -- 'quick', 'full', 'category-specific'
    model VARCHAR(100),
    subset_percent INTEGER DEFAULT 100,

    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER,

    -- Scores (populated on completion)
    composite_score DECIMAL(5,4),
    quality_score DECIMAL(5,4),
    speed_score DECIMAL(5,4),
    cost_score DECIMAL(5,4),
    streaming_score DECIMAL(5,4),
    multimodal_score DECIMAL(5,4),

    -- Metadata
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    metadata JSONB
);

-- Task results table
CREATE TABLE task_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES scoring_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Task info
    task_id VARCHAR(100) NOT NULL,
    benchmark VARCHAR(50) NOT NULL,
    task_type VARCHAR(50),

    -- Result
    success BOOLEAN,
    response_text TEXT,
    error TEXT,

    -- Scores
    quality_score DECIMAL(5,4),

    -- Metrics
    latency_seconds DECIMAL(10,3),
    ttft_seconds DECIMAL(10,3),
    avg_tps DECIMAL(10,2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10,6),

    -- Streaming metrics
    continuity_score DECIMAL(5,4),
    max_gap_seconds DECIMAL(10,3),

    -- Full data
    streaming_metrics JSONB,
    metadata JSONB
);

-- Competitors table (optional, for registered competitors)
CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    name VARCHAR(200) NOT NULL,
    team VARCHAR(200),
    description TEXT,
    container_image TEXT NOT NULL,
    github_url TEXT,

    -- Best scores (updated after each run)
    best_composite_score DECIMAL(5,4),
    best_run_id UUID REFERENCES scoring_runs(id),

    -- Status
    verified BOOLEAN DEFAULT FALSE,
    is_baseline BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX idx_scoring_runs_status ON scoring_runs(status);
CREATE INDEX idx_scoring_runs_created_at ON scoring_runs(created_at DESC);
CREATE INDEX idx_scoring_runs_competitor_id ON scoring_runs(competitor_id);
CREATE INDEX idx_task_results_run_id ON task_results(run_id);
CREATE INDEX idx_task_results_benchmark ON task_results(benchmark);
CREATE INDEX idx_competitors_best_score ON competitors(best_composite_score DESC NULLS LAST);
```

### FR-2: API Endpoints

```python
# scoring_service/main.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI(title="Janus Scoring Service", version="1.0.0")

# ─── Run Management ───────────────────────────────────────────────────────────

@app.post("/api/runs", response_model=ScoringRunResponse)
async def create_scoring_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
) -> ScoringRunResponse:
    """
    Create a new scoring run.

    Request body:
    {
        "target_type": "url" | "container" | "competitor_id",
        "target_url": "http://...",  // if target_type == "url"
        "container_image": "...",     // if target_type == "container"
        "competitor_id": "...",       // if target_type == "competitor_id"
        "suite": "quick" | "full" | "research" | "tool_use" | "multimodal" | "streaming" | "cost",
        "model": "deepseek-reasoner",
        "subset_percent": 100
    }

    Returns the created run with pending status.
    """
    run = await create_run_in_db(request)
    background_tasks.add_task(execute_scoring_run, run.id)
    return run


@app.get("/api/runs", response_model=list[ScoringRunResponse])
async def list_scoring_runs(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    competitor_id: Optional[str] = None,
) -> list[ScoringRunResponse]:
    """List scoring runs with optional filters."""
    return await get_runs_from_db(limit, offset, status, competitor_id)


@app.get("/api/runs/{run_id}", response_model=ScoringRunDetailResponse)
async def get_scoring_run(run_id: str) -> ScoringRunDetailResponse:
    """Get detailed run info including task results."""
    run = await get_run_from_db(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/runs/{run_id}/stream")
async def stream_run_progress(run_id: str) -> StreamingResponse:
    """
    Stream run progress via Server-Sent Events.

    Events:
    - progress: {"current": 10, "total": 100, "latest_result": {...}}
    - completed: {"composite_score": 0.85, ...}
    - failed: {"error": "..."}
    """
    async def event_stream():
        while True:
            run = await get_run_from_db(run_id)
            if run.status == "completed":
                yield f"event: completed\ndata: {run.model_dump_json()}\n\n"
                break
            elif run.status == "failed":
                yield f"event: failed\ndata: {{'error': '{run.error}'}}\n\n"
                break
            else:
                progress = {
                    "current": run.progress_current,
                    "total": run.progress_total,
                    "status": run.status,
                }
                yield f"event: progress\ndata: {json.dumps(progress)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.delete("/api/runs/{run_id}")
async def cancel_scoring_run(run_id: str) -> dict:
    """Cancel a running or pending scoring run."""
    await cancel_run(run_id)
    return {"status": "cancelled"}


# ─── Results & Analytics ──────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/results", response_model=list[TaskResultResponse])
async def get_run_results(
    run_id: str,
    benchmark: Optional[str] = None,
    success_only: bool = False,
) -> list[TaskResultResponse]:
    """Get task results for a specific run."""
    return await get_results_from_db(run_id, benchmark, success_only)


@app.get("/api/runs/{run_id}/summary", response_model=RunSummaryResponse)
async def get_run_summary(run_id: str) -> RunSummaryResponse:
    """
    Get aggregate summary for a run.

    Returns:
    {
        "run_id": "...",
        "composite_score": 0.85,
        "scores": {"quality": 0.90, "speed": 0.82, ...},
        "by_benchmark": {
            "janus_research": {"score": 0.88, "passed": 95, "failed": 5},
            ...
        },
        "metrics": {
            "avg_latency_seconds": 2.5,
            "avg_ttft_seconds": 0.45,
            "total_tokens": 150000,
            "total_cost_usd": 1.25
        }
    }
    """
    return await compute_run_summary(run_id)


# ─── Competitors ──────────────────────────────────────────────────────────────

@app.get("/api/competitors", response_model=list[CompetitorResponse])
async def list_competitors(
    include_baselines: bool = True,
    verified_only: bool = False,
) -> list[CompetitorResponse]:
    """List all registered competitors."""
    return await get_competitors_from_db(include_baselines, verified_only)


@app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    limit: int = 50,
    verified_only: bool = False,
) -> list[LeaderboardEntry]:
    """
    Get the competition leaderboard.

    Returns competitors ranked by best_composite_score.
    """
    return await get_leaderboard_from_db(limit, verified_only)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "janus-scoring"}
```

### FR-3: Scoring Run Execution

```python
# scoring_service/executor.py

from janus_bench import BenchmarkRunner, Settings, load_suite

async def execute_scoring_run(run_id: str) -> None:
    """Execute a scoring run in the background."""
    run = await get_run_from_db(run_id)

    try:
        # Update status to running
        await update_run_status(run_id, "running", started_at=datetime.now())

        # Determine target URL
        if run.target_type == "url":
            target_url = run.target_url
        elif run.target_type == "container":
            # Start container in Sandy and get URL
            target_url = await start_container_in_sandbox(run.container_image)
        elif run.target_type == "competitor_id":
            competitor = await get_competitor(run.competitor_id)
            target_url = await start_container_in_sandbox(competitor.container_image)

        # Configure bench runner
        settings = Settings(
            target_url=target_url,
            model=run.model or "deepseek-reasoner",
            subset_percent=run.subset_percent,
            seed=42,
        )

        runner = BenchmarkRunner(settings)

        # Get total tasks
        tasks = load_suite(run.suite)
        await update_run_progress(run_id, 0, len(tasks))

        # Run with progress callback
        async def on_progress(current: int, total: int, result: TaskResult):
            await update_run_progress(run_id, current, total)
            await store_task_result(run_id, result)

        report = await runner.run_suite(
            run.suite,
            progress_callback=on_progress,
        )

        # Update with final scores
        await update_run_completed(
            run_id,
            composite_score=report.composite_score,
            quality_score=report.quality_score,
            speed_score=report.speed_score,
            cost_score=report.cost_score,
            streaming_score=report.streaming_score,
            multimodal_score=report.multimodal_score,
            completed_at=datetime.now(),
        )

        # Update competitor best score if applicable
        if run.competitor_id:
            await update_competitor_best_score(
                run.competitor_id,
                report.composite_score,
                run_id,
            )

    except Exception as e:
        await update_run_status(run_id, "failed", error=str(e))
        raise
    finally:
        await runner.close()

        # Cleanup sandbox if used
        if run.target_type in ("container", "competitor_id"):
            await cleanup_sandbox(target_url)
```

### FR-4: Sandy Integration

```python
# scoring_service/sandy.py

import httpx
from typing import Optional

SANDY_API_URL = "https://sandbox.janus.rodeo"

async def start_container_in_sandbox(
    container_image: str,
    timeout_seconds: int = 300,
) -> str:
    """
    Start a competitor container in a Sandy sandbox.

    Returns the URL to access the container.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{SANDY_API_URL}/sandboxes",
            json={
                "image": container_image,
                "ports": [8080],
                "timeout_seconds": timeout_seconds,
                "resources": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "gpu": True,  # If available
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        sandbox_id = data["sandbox_id"]
        return f"http://{sandbox_id}.sandbox.janus.rodeo:8080"


async def cleanup_sandbox(sandbox_url: str) -> None:
    """Terminate a sandbox."""
    # Extract sandbox_id from URL
    sandbox_id = sandbox_url.split("//")[1].split(".")[0]

    async with httpx.AsyncClient(timeout=30) as client:
        await client.delete(f"{SANDY_API_URL}/sandboxes/{sandbox_id}")


async def health_check_sandbox(sandbox_url: str, max_retries: int = 30) -> bool:
    """Wait for container to be ready."""
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(max_retries):
            try:
                response = await client.get(f"{sandbox_url}/health")
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            await asyncio.sleep(1)

    return False
```

### FR-5: Pydantic Models

```python
# scoring_service/models.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class CreateRunRequest(BaseModel):
    target_type: str  # "url", "container", "competitor_id"
    target_url: Optional[str] = None
    container_image: Optional[str] = None
    competitor_id: Optional[UUID] = None
    suite: str = "quick"
    model: Optional[str] = None
    subset_percent: int = 100

class ScoringRunResponse(BaseModel):
    id: UUID
    created_at: datetime
    target_type: str
    target_url: Optional[str]
    container_image: Optional[str]
    competitor_id: Optional[UUID]
    suite: str
    status: str
    progress_current: int
    progress_total: Optional[int]
    composite_score: Optional[float]
    quality_score: Optional[float]
    speed_score: Optional[float]
    cost_score: Optional[float]
    streaming_score: Optional[float]
    multimodal_score: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]

class TaskResultResponse(BaseModel):
    id: UUID
    task_id: str
    benchmark: str
    task_type: Optional[str]
    success: bool
    quality_score: Optional[float]
    latency_seconds: float
    ttft_seconds: Optional[float]
    avg_tps: Optional[float]
    total_tokens: Optional[int]
    cost_usd: Optional[float]
    continuity_score: Optional[float]
    error: Optional[str]

class RunSummaryResponse(BaseModel):
    run_id: UUID
    composite_score: float
    scores: dict[str, float]
    by_benchmark: dict[str, dict]
    metrics: dict[str, float]

class CompetitorResponse(BaseModel):
    id: UUID
    name: str
    team: Optional[str]
    container_image: str
    best_composite_score: Optional[float]
    verified: bool
    is_baseline: bool

class LeaderboardEntry(BaseModel):
    rank: int
    competitor: CompetitorResponse
    best_run_id: Optional[UUID]
    scores: dict[str, float]
```

## Non-Functional Requirements

### NFR-1: Performance

- Scoring runs should not block the API
- Progress updates should stream in real-time
- Database queries should use indexes
- Support at least 5 concurrent scoring runs

### NFR-2: Reliability

- Failed runs should be retryable
- Sandbox cleanup on failure
- Database transactions for consistency
- Graceful shutdown

### NFR-3: Security

- Validate container images
- Rate limit run creation
- No PII in task results
- Secure sandbox isolation

## Acceptance Criteria

- [ ] Database schema created in Neon
- [ ] API endpoints implemented and tested
- [ ] Scoring runs execute against janus-bench
- [ ] Progress streaming works
- [ ] Sandy integration functional
- [ ] Leaderboard populates from runs
- [ ] Health endpoint returns 200
- [ ] Deployed to Render

## Deployment Configuration

### Render Blueprint (`render.yaml`)

```yaml
services:
  - type: web
    name: janus-scoring-service
    runtime: python
    region: oregon
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn scoring_service.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: janus-scoring-db
          property: connectionString
      - key: SANDY_API_URL
        value: https://sandbox.janus.rodeo
      - key: JUDGE_URL
        sync: false
      - key: JUDGE_API_KEY
        sync: false

databases:
  - name: janus-scoring-db
    plan: free
    region: oregon
```

### Alternative: Neon Database

Use Neon MCP to create the database:
- Project: janus-scoring
- Region: us-east-1
- Branch: main

Environment variable:
```
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb
```

## Files to Create

```
scoring-service/
├── pyproject.toml
├── requirements.txt
├── scoring_service/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── models.py         # Pydantic models
│   ├── database.py       # Database connection
│   ├── executor.py       # Run execution
│   ├── sandy.py          # Sandy integration
│   └── migrations/
│       └── 001_initial.sql
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   └── test_executor.py
└── README.md
```

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Benchmark definitions
- `specs/36_janus_bench_ui_section.md` - UI for bench runner
- `specs/54_baseline_containerization.md` - Container specs
- `specs/56_scoring_ui_page.md` - Frontend for this service
