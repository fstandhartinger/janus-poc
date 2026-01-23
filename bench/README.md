# Janus Benchmark Runner

Evaluation harness for Janus competitors. Measures quality, speed, cost, streaming continuity, and multimodal handling.

## Installation

```bash
cd bench
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: enable CLIP-based image scoring
pip install -e ".[dev,multimodal]"
```

## Usage

### Run a Benchmark Suite

```bash
# Run against local gateway
janus-bench run --target http://localhost:8000 --suite public/dev

# Run Janus intelligence suite
janus-bench run --target http://localhost:8000 --suite janus/intelligence

# Run against deployed gateway
janus-bench run --target https://janus.example.com --suite public/dev

# Specify model and output file
janus-bench run --target http://localhost:8000 --suite public/dev --model janus-baseline-agent-cli --output results.json

# Run a deterministic subset (10% sample)
janus-bench run --target http://localhost:8000 --suite public/dev --subset 10 --seed 42

# Run a single Janus benchmark
janus-bench run --target http://localhost:8000 --suite janus/intelligence --benchmark janus_streaming
```

### List Available Suites

```bash
janus-bench list-suites
```

### List Available Benchmarks

```bash
janus-bench list-benchmarks
```

### View Saved Report

```bash
janus-bench show results.json
```

## Scoring

The composite score (0-100) is calculated from weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Quality | 40% | Response correctness for research + tool-use tasks |
| Speed | 20% | TTFT and token throughput (TPS) for streaming tasks |
| Cost | 15% | Token usage, USD cost, sandbox seconds |
| Streaming | 15% | Continuity score based on streaming metrics |
| Multimodal | 10% | Image generation, vision understanding, mixed media, and routing (CLIP-based when available) |

## Benchmark Suites

- **public/train** - Visible training data for iteration
- **public/dev** - Visible development data, scored
- **private/test** - Hidden test data for final evaluation (stubs in PoC)
- **janus/intelligence** - Full Janus Intelligence benchmark suite

## Task Types

- **chat_quality** - Simple Q&A for quality measurement
- **research** - Fact-finding tasks
- **tool_use** - Function calling and tool integration
- **coding** - Code generation tasks
- **streaming** - Tasks that test streaming continuity
- **multimodal** - Image generation, image understanding, and multimodal routing
- **cost** - Token efficiency tasks

## Janus Intelligence Benchmarks

The Janus suite is organized into five benchmarks (all under the **Janus Intelligence** category):

- **janus_research** - Web search and synthesis tasks (100 items)
- **janus_tool_use** - Function calling and tool integration tasks (80 items)
- **janus_multimodal** - Image/vision tasks (60 items)
- **janus_streaming** - Streaming quality metrics (50 items)
- **janus_cost** - Token efficiency evaluation (40 items)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JANUS_BENCH_TARGET_URL` | `http://localhost:8000` | Target gateway URL |
| `JANUS_BENCH_MODEL` | `janus-baseline-agent-cli` | Model name for requests |
| `JANUS_BENCH_REQUEST_TIMEOUT` | `300` | Request timeout in seconds |
| `JANUS_BENCH_SEED` | `42` | Random seed for reproducibility |
| `JANUS_BENCH_SUBSET_PERCENT` | `100` | Task subset percentage (1-100) |

## Output Format

Results are saved as JSON with the following structure:

```json
{
  "run_id": "abc12345",
  "suite": "public/dev",
  "target_url": "http://localhost:8000",
  "model": "janus-baseline-agent-cli",
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
