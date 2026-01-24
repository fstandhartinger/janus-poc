# Baseline Test Suite

This folder contains shared smoke tests that exercise both baseline services.

## Prerequisites

- `baseline-agent-cli` running on `http://localhost:8001`
- `baseline-langchain` running on `http://localhost:8002`

You can override the defaults with:

- `BASELINE_CLI_URL`
- `BASELINE_LANGCHAIN_URL`
- `BASELINE_CLI_MODEL`
- `BASELINE_LANGCHAIN_MODEL`

## Run Smoke Tests

```bash
pytest tests/smoke -v -m smoke
```

## Notes

- If a service is not reachable, the smoke tests will skip.
- When baseline services are in mock mode, assertions relax to basic quality checks.
