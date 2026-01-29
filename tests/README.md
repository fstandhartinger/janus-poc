# Janus Test Suite

This folder contains shared smoke, integration, and visual tests across the
gateway, baselines, and UI.

## Prerequisites

- `gateway` running on `http://localhost:8000`
- `baseline-agent-cli` running on `http://localhost:8081`
- `baseline-langchain` running on `http://localhost:8082`
- `ui` running on `http://localhost:3000`

You can override the defaults with:

- `TEST_MODE=local|deployed|both`
- `TEST_GATEWAY_URL`, `TEST_BASELINE_CLI_URL`, `TEST_BASELINE_LANGCHAIN_URL`, `TEST_UI_URL`
- `TEST_GATEWAY_DEPLOYED_URL`, `TEST_BASELINE_CLI_DEPLOYED_URL`,
  `TEST_BASELINE_LANGCHAIN_DEPLOYED_URL`, `TEST_UI_DEPLOYED_URL`
- `TEST_BASELINE_CLI_MODEL`, `TEST_BASELINE_LANGCHAIN_MODEL`
- `TEST_SCREENSHOT_DIR`

Legacy variables (`BASELINE_*`) are still supported.

## Run Smoke Tests

```bash
pytest tests/smoke -v -m smoke
```

## Run Baseline Smoke Tests (Gateway)

```bash
./scripts/smoke-baselines.sh
pytest tests/smoke/test_baseline_gateway.py -v -m smoke_baseline
```

## Run Integration Tests

```bash
pytest tests/integration -v -m integration
```

## Run Core Demo E2E Tests

```bash
pytest tests/e2e -v -m e2e
```

## Run Visual Tests

```bash
pytest tests/visual -v -m visual
```

## Run the Full Suite

```bash
./scripts/run-tests.sh local
./scripts/run-tests.sh deployed
./scripts/run-tests.sh both
```

## Notes

- If a service is not reachable, the smoke tests will skip.
- When baseline services are in mock mode, assertions relax to basic quality checks.
