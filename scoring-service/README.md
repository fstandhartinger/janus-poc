# Janus Scoring Service

FastAPI service that executes Janus benchmark suites against competitor targets, stores run results, and provides streaming progress updates.

## Local Development

```bash
cd scoring-service
python -m venv .venv && source .venv/bin/activate
pip install -e "../bench"
pip install -r requirements.txt
uvicorn scoring_service.main:app --reload --port 8100
```

## Configuration

Required:
- `DATABASE_URL` (PostgreSQL or SQLite for local dev)

Optional:
- `SANDY_API_URL` (default: https://sandbox.janus.rodeo)
- `JUDGE_URL` (optional LLM judge base URL)
- `JUDGE_API_KEY` (optional judge API key)
- `JUDGE_MODEL` (optional judge model override)
- `SCORING_MAX_CONCURRENT_RUNS` (default: 5)
- `SCORING_SSE_POLL_INTERVAL` (default: 2.0 seconds)
- `SCORING_RUN_RATE_LIMIT` (default: 5 requests)
- `SCORING_RUN_RATE_WINDOW_SECONDS` (default: 60 seconds)
- `SCORING_INIT_DB` (set to `true` to auto-create tables on startup for local dev)

## Endpoints

- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/stream`
- `GET /api/runs/{run_id}/results`
- `GET /api/runs/{run_id}/summary`
- `DELETE /api/runs/{run_id}`
- `GET /api/competitors`
- `GET /api/leaderboard`
- `GET /health`

## Tests

```bash
cd scoring-service
pip install -e "../bench"
pip install -e ".[dev]"
pytest
```
