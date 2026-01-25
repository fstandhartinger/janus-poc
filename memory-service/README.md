# Janus Memory Service

A lightweight FastAPI service for extracting and retrieving user memories.

## Environment

- `DATABASE_URL` (required)
- `CHUTES_API_KEY` (required for LLM extraction)
- `MEMORY_INIT_DB` (set `true` to auto-create tables)
- `MEMORY_MAX_MEMORIES_PER_USER` (default: 100)
- `MEMORY_RATE_LIMIT_PER_MINUTE` (default: 60)
- `MEMORY_RATE_LIMIT_WINDOW_SECONDS` (default: 60)
- `MEMORY_LLM_BASE_URL` (default: https://llm.chutes.ai/v1)
- `MEMORY_LLM_MODEL` (default: GLM-4-9B-0414-fast)
- `MEMORY_LLM_TEMPERATURE` (default: 0.1)
- `MEMORY_LLM_MAX_TOKENS` (default: 1000)

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export DATABASE_URL=sqlite+aiosqlite:///./memory.db
export CHUTES_API_KEY=your-key
export MEMORY_INIT_DB=true
uvicorn memory_service.main:app --reload
```

## Tests

```bash
pip install -e .[dev]
pytest
```
