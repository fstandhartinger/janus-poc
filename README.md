# Janus PoC

A competitive, OpenAI-compatible intelligence API proof-of-concept. Miners submit containers that expose `/v1/chat/completions` and stream continuously.

## Components

| Component | Description | Port |
|-----------|-------------|------|
| [Gateway](gateway/) | OpenAI-compatible proxy and routing | 8000 |
| [Chat UI](ui/) | ChatGPT-like interface with streaming | 3000 |
| [Baseline](baseline/) | Reference competitor implementation | 8001 |
| [Bench](bench/) | Evaluation harness and scoring | CLI |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+

### Run Locally

```bash
# Terminal 1: Gateway
cd gateway
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_gateway.main

# Terminal 2: Baseline Competitor
cd baseline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_baseline.main

# Terminal 3: Chat UI
cd ui
npm install
npm run dev
```

Open http://localhost:3000 to use the chat interface.

### Run Benchmarks

```bash
cd bench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
janus-bench run --target http://localhost:8000 --suite public/dev
```

## Documentation

- [Architecture](docs/architecture.md) - System design and data flows
- [Runbook](docs/runbook.md) - Operations guide and troubleshooting

## Specifications

All implementation follows the detailed specifications in `specs/`:

| # | Spec | Status |
|---|------|--------|
| 00 | [Overview](specs/00_overview.md) | Complete |
| 01 | [Scope MVP](specs/01_scope_mvp.md) | Complete |
| 02 | [Architecture](specs/02_architecture.md) | Complete |
| 03 | [Components](specs/03_components.md) | Complete |
| 04 | [OpenAI API Compatibility](specs/04_openai_api_compat.md) | Complete |
| 05 | [Streaming Contract](specs/05_streaming_contract.md) | Complete |
| 06 | [Artifacts and Files](specs/06_artifacts_and_files.md) | Complete |
| 07 | [Security Guardrails](specs/07_security_guardrails.md) | Complete |
| 08 | [Sandy Integration](specs/08_sandy_integration.md) | Complete |
| 09 | [Reference CLI Agent](specs/09_reference_impl_cli_agent.md) | Complete |
| 10 | [Competitor Submission](specs/10_competitor_submission.md) | Complete |
| 11 | [Chat UI](specs/11_chat_ui.md) | Complete |
| 12 | [Benchmarking](specs/12_benchmarking_scoring.md) | Complete |
| 13 | [Ops & Observability](specs/13_ops_observability.md) | Complete |
| 14 | [Roadmap](specs/14_roadmap_milestones.md) | Complete |
| 15 | [Component Marketplace](specs/15_component_marketplace.md) | Complete |
| 16 | [Bench Runner Integration](specs/16_bench_runner_integration.md) | Complete |
| 17 | [Documentation](specs/17_documentation_and_diagrams.md) | Complete |

## Testing

```bash
# Gateway tests
cd gateway && pytest

# Baseline tests
cd baseline && pytest

# Benchmark runner tests
cd bench && pytest

# UI tests
cd ui && npm test
```

## Environment Variables

See individual component READMEs for full configuration:

| Variable | Description |
|----------|-------------|
| `JANUS_PORT` | Gateway port (default: 8000) |
| `BASELINE_PORT` | Baseline port (default: 8001) |
| `NEXT_PUBLIC_GATEWAY_URL` | Gateway URL for UI |
| `SANDY_BASE_URL` | Sandy sandbox service URL |
| `SANDY_API_KEY` | Sandy API key |
| `BASELINE_OPENAI_API_KEY` | OpenAI API key for baseline |

## Project Structure

```
janus-poc/
├── gateway/          # FastAPI backend (Python 3.11)
├── ui/               # Next.js frontend (Node 20+)
├── baseline/         # Reference competitor
├── bench/            # Benchmark runner CLI
├── specs/            # Implementation specifications
├── docs/             # Architecture and runbook
└── scripts/          # Automation scripts
```

## Notes

This repository is nested inside the Chutes monorepo but is intentionally **ignored** by the
monorepo `.gitignore`. It is meant to be managed as its own repo.
