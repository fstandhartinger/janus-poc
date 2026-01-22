# Janus Benchmark Runner

Evaluation harness for Janus competitors. Measures quality, speed, cost, streaming continuity, and multimodal handling.

## Installation

```bash
cd bench
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

### Run a Benchmark Suite

```bash
# Run against local gateway
janus-bench run --target http://localhost:8000 --suite public/dev

# Run against deployed gateway
janus-bench run --target https://janus.example.com --suite public/dev

# Specify model and output file
janus-bench run --target http://localhost:8000 --suite public/dev --model janus-baseline --output results.json
```

### List Available Suites

```bash
janus-bench list-suites
```

### View Saved Report

```bash
janus-bench show results.json
```

## Scoring

The composite score (0-100) is calculated from weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Quality | 45% | Response correctness based on expected answers/keywords |
| Speed | 20% | P50 latency and time to first token (TTFT) |
| Cost | 15% | Token usage, USD cost, sandbox seconds |
| Streaming | 10% | TTFT, max gap between events, chunk count |
| Multimodal | 10% | Image input acknowledgment and processing |

## Benchmark Suites

- **public/train** - Visible training data for iteration
- **public/dev** - Visible development data, scored
- **private/test** - Hidden test data for final evaluation (stubs in PoC)

## Task Types

- **chat_quality** - Simple Q&A for quality measurement
- **research** - Fact-finding tasks
- **coding** - Code generation tasks
- **streaming** - Tasks that test streaming continuity
- **multimodal** - Tasks with image input

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUS_BENCH_TARGET_URL` | `http://localhost:8000` | Target gateway URL |
| `JANUS_BENCH_MODEL` | `janus-baseline` | Model name for requests |
| `JANUS_BENCH_REQUEST_TIMEOUT` | `300` | Request timeout in seconds |
| `JANUS_BENCH_SEED` | `42` | Random seed for reproducibility |

## Output Format

Results are saved as JSON with the following structure:

```json
{
  "run_id": "abc12345",
  "suite": "public/dev",
  "target_url": "http://localhost:8000",
  "model": "janus-baseline",
  "started_at": "2026-01-22T12:00:00Z",
  "completed_at": "2026-01-22T12:05:00Z",
  "composite_score": 85.5,
  "quality_score": 90.0,
  "speed_score": 80.0,
  "cost_score": 85.0,
  "streaming_score": 75.0,
  "multimodal_score": 90.0,
  "total_tasks": 10,
  "passed_tasks": 9,
  "failed_tasks": 1,
  "avg_latency_seconds": 2.5,
  "p50_latency_seconds": 2.0,
  "avg_ttft_seconds": 0.8,
  "max_gap_seconds": 1.5,
  "total_tokens": 5000,
  "total_cost_usd": 0.05,
  "results": [...]
}
```

## Development

### Run Tests

```bash
pytest
```

### Run Type Checks

```bash
mypy janus_bench
```

### Run Linter

```bash
ruff check janus_bench
```
