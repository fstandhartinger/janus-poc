# Janus PoC Runbook

Operational guide for running, validating, and troubleshooting the Janus PoC.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Sandy service access (optional for full baseline functionality)

### Local Development Setup

```bash
# 1. Clone and navigate
cd janus-poc

# 2. Start the Gateway
cd gateway
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_gateway.main
# Gateway runs on http://localhost:8000

# 3. Start the Baseline Competitor (new terminal)
cd baseline-agent-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
BASELINE_AGENT_CLI_PORT=8081 python -m janus_baseline_agent_cli.main
# Baseline runs on http://localhost:8081

# 4. (Optional) Start the Baseline LangChain competitor (new terminal)
cd baseline-langchain
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
BASELINE_LANGCHAIN_PORT=8082 python -m janus_baseline_langchain.main
# Baseline LangChain runs on http://localhost:8082

# 5. Start the Chat UI (new terminal)
cd ui
npm install
npm run dev
# UI runs on http://localhost:3000

# 6. (Optional) Run Benchmarks
cd bench
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
janus-bench run --target http://localhost:8000 --suite public/dev
```

## Health Checks

### Gateway

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}
```

### Baseline

```bash
curl http://localhost:8081/health
# Expected: {"status":"ok","version":"0.1.0"}
```

### Baseline LangChain

```bash
curl http://localhost:8082/health
# Expected: {"status":"ok","version":"0.1.0"}
```

### UI

```bash
curl http://localhost:3000
# Expected: HTML page loads
```

## Validation Checklist

### Pre-Deployment

- [ ] All unit tests pass: `cd gateway && pytest` / `cd baseline-agent-cli && pytest` / `cd bench && pytest`
- [ ] Baseline LangChain tests pass: `cd baseline-langchain && pytest`
- [ ] Type checks pass: `cd gateway && mypy janus_gateway`
- [ ] UI builds: `cd ui && npm run build`
- [ ] Lint passes: `ruff check gateway/ baseline-agent-cli/ bench/`

### Post-Deployment

- [ ] Health endpoints return 200
- [ ] UI loads and can send a message
- [ ] Streaming works (incremental text appears)
- [ ] Benchmark suite runs: `janus-bench run --suite public/dev`

## Common Operations

### Run Unit Tests

```bash
# Gateway
cd gateway && pytest -v

# Baseline
cd baseline-agent-cli && pytest -v

# Baseline LangChain
cd baseline-langchain && pytest -v

# Benchmark runner
cd bench && pytest -v
```

### Run Type Checks

```bash
cd gateway && mypy janus_gateway
cd baseline-agent-cli && mypy janus_baseline_agent_cli
cd baseline-langchain && mypy janus_baseline_langchain
cd bench && mypy janus_bench
```

### Run Linter

```bash
ruff check gateway/ baseline-agent-cli/ baseline-langchain/ bench/
```

### Run Full Benchmark Suite

```bash
cd bench
source .venv/bin/activate
janus-bench run --target http://localhost:8000 --suite public/dev --output results.json
```

### View Benchmark Results

```bash
janus-bench show results.json
```

## Troubleshooting

### Gateway won't start

**Symptom**: `ModuleNotFoundError: No module named 'janus_gateway'`

**Fix**: Ensure you installed the package:
```bash
cd gateway
pip install -e ".[dev]"
```

### Streaming not working

**Symptom**: Response comes all at once instead of incrementally

**Possible causes**:
1. `stream: true` not set in request
2. Proxy buffering (check nginx/CDN settings)
3. Client not processing SSE events

**Debug**:
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "janus-baseline-agent-cli", "messages": [{"role": "user", "content": "Count to 5"}], "stream": true}'
```

### Baseline returns errors

**Symptom**: 500 errors from baseline competitor

**Check**:
1. OpenAI API key configured: `echo $BASELINE_AGENT_CLI_OPENAI_API_KEY`
2. Sandy service reachable (if using complex path)
3. Logs: `tail -f logs/baseline-agent-cli.log`

### Benchmark runner timeout

**Symptom**: Tasks timeout during benchmark run

**Fix**: Increase timeout:
```bash
janus-bench run --timeout 600 --suite public/dev
```

### UI can't connect to gateway

**Symptom**: Network error in browser console

**Check**:
1. Gateway is running: `curl http://localhost:8000/health`
2. CORS is enabled (default: allows all origins)
3. Environment variable: `NEXT_PUBLIC_GATEWAY_URL`

## Logs

### Gateway Logs

```bash
# JSON format (default in production)
JANUS_LOG_FORMAT=json python -m janus_gateway.main

# Console format (development)
JANUS_LOG_FORMAT=console python -m janus_gateway.main
```

### Key Log Fields

| Field | Description |
|-------|-------------|
| `request_id` | Unique request identifier |
| `competitor_id` | Selected competitor |
| `latency` | Request duration |
| `status` | HTTP status code |
| `bytes_streamed` | Total bytes sent |

### Example Log Analysis

```bash
# Find slow requests (latency > 5s)
cat logs/gateway.json | jq 'select(.latency > 5)'

# Count errors by type
cat logs/gateway.json | jq 'select(.level == "error") | .error' | sort | uniq -c
```

## Metrics

### Gateway Metrics (if enabled)

```bash
curl http://localhost:8000/metrics
```

### Benchmark Metrics

After running benchmarks, check the JSON output:

```bash
jq '.avg_latency_seconds, .avg_ttft_seconds, .max_gap_seconds' results.json
```

## Recovery Procedures

### Reset Gateway State

The gateway is stateless. Simply restart:
```bash
pkill -f "janus_gateway"
python -m janus_gateway.main
```

### Clear Artifact Cache

```bash
rm -rf /tmp/janus_artifacts/*
```

### Rebuild UI

```bash
cd ui
rm -rf .next node_modules
npm install
npm run build
```

## Deployment (Render)

### Deploy via CLI

```bash
# Assumes render.yaml is configured
render deploy
```

### Monitor Deployment

```bash
# View deploy logs
render logs --service janus-gateway

# Check health after deploy
curl https://janus-gateway.onrender.com/health
```

### Rollback

```bash
# List recent deploys
render deploys --service janus-gateway

# Rollback to previous
render rollback --service janus-gateway --deploy <deploy-id>
```
