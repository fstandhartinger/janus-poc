# Janus PoC

**[janus.rodeo](https://janus-ui.onrender.com)** — A competitive, OpenAI-compatible intelligence API where miners compete to build the best universal agent. Anything in, anything out.

> *Janus* is the Roman god of beginnings, transitions, and duality — looking to the past and future simultaneously. Here, Janus rides the bull: a nod to the crypto-bullish ethos and the rodeo-style miner competition.

## Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| **Janus UI** | https://janus-ui.onrender.com | [![UI](https://img.shields.io/badge/live-online-63D297)](https://janus-ui.onrender.com) |
| **Janus Gateway** | https://janus-gateway-bqou.onrender.com | [![Gateway](https://img.shields.io/badge/live-online-63D297)](https://janus-gateway-bqou.onrender.com/health) |
| **Janus Baseline Agent** | https://janus-baseline-agent.onrender.com | [![Baseline](https://img.shields.io/badge/live-online-63D297)](https://janus-baseline-agent.onrender.com/health) |
| **Janus Baseline LangChain** | https://janus-baseline-langchain.onrender.com | [![Baseline](https://img.shields.io/badge/live-online-63D297)](https://janus-baseline-langchain.onrender.com/health) |

## Components

| Component | Description | Local Port |
|-----------|-------------|------------|
| [Gateway](gateway/) | OpenAI-compatible proxy and routing | 8000 |
| [Chat UI](ui/) | Next.js frontend with landing, chat, competition & marketplace pages | 3000 |
| [Baseline Agent CLI](baseline-agent-cli/) | Reference competitor implementation | 8001 |
| [Baseline LangChain](baseline-langchain/) | LangChain-based baseline competitor | 8002 |
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
cd baseline-agent-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_baseline_agent_cli.main

# Terminal 3 (optional): Baseline LangChain
cd baseline-langchain
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m janus_baseline_langchain.main

# Terminal 4: Chat UI
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
| 18 | [Landing Page](specs/18_landing_page.md) | **Pending** |
| 19 | [Competition Page](specs/19_competition_page.md) | **Pending** |
| 20 | [Marketplace Page](specs/20_marketplace_page.md) | **Pending** |

## Testing

Test matrix (component -> category):

| Component | Category | Primary checks |
|-----------|----------|----------------|
| Gateway | Unit/Integration | `cd gateway && pytest` |
| Baseline Agent CLI | Unit/Integration | `cd baseline-agent-cli && pytest` |
| Bench | Unit/Integration | `cd bench && pytest` |
| UI | UI | `cd ui && npm test` |
| End-to-end | Smoke | Run gateway + baseline + UI and verify `/health` + a chat request |

```bash
# Gateway tests
cd gateway && pytest

# Baseline tests
cd baseline-agent-cli && pytest

# Baseline LangChain tests
cd baseline-langchain && pytest

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
| `BASELINE_AGENT_CLI_PORT` | Baseline agent CLI port (default: 8001) |
| `BASELINE_LANGCHAIN_PORT` | Baseline LangChain port (default: 8002) |
| `NEXT_PUBLIC_GATEWAY_URL` | Gateway URL for UI |
| `SANDY_BASE_URL` | Sandy sandbox service URL |
| `SANDY_API_KEY` | Sandy API key |
| `BASELINE_AGENT_CLI_OPENAI_API_KEY` | OpenAI API key for baseline |
| `BASELINE_LANGCHAIN_OPENAI_API_KEY` | OpenAI API key for baseline LangChain |

## Project Structure

```
janus-poc/
├── gateway/          # FastAPI backend (Python 3.11)
├── ui/               # Next.js frontend (Node 20+)
├── baseline-agent-cli/ # Reference competitor
├── baseline-langchain/ # LangChain baseline competitor
├── bench/            # Benchmark runner CLI
├── specs/            # Implementation specifications
├── docs/             # Architecture and runbook
└── scripts/          # Automation scripts
```

## The Vision

Janus is both the **competition** and the **product**: an open, permissionless intelligence API that can handle *anything in, anything out* — multimodal, tool-using, with streaming intermediate steps.

### How It Works

1. **Miners/Competitors** submit arbitrary Docker containers that expose an OpenAI Chat Completions compatible API
2. Behind the scenes, they can do whatever they want: CLI agents, n8n workflows, custom logic, toolchains
3. The platform enforces the API contract + continuous streaming + guardrails
4. A **composite score** (quality, speed, cost, streaming continuity, modality) determines rankings
5. The best implementations earn rewards

### Why CLI Agents?

The industry has converged on generalist CLI agents (Claude Code, OpenHands, Aider, etc.) as the most efficient way to build intelligent systems. These agents:

- Handle coding, research, routing, and tool use with a single runtime
- Require isolated sandboxes (filesystem + internet + browser + terminal)
- Operate in "YOLO mode" safely within containers
- Outperform hand-built workflows with far less engineering

Our **reference baseline** demonstrates this architecture: a thin OpenAI-compatible wrapper around a CLI agent running in a sandbox.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Janus UI                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Landing  │  │  Chat    │  │Competition│  │   Marketplace   │ │
│  │  Page    │  │  App     │  │   Page   │  │      Page       │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Janus Gateway                               │
│  • OpenAI-compatible /v1/chat/completions                       │
│  • Competitor routing & selection                               │
│  • Streaming pass-through (reasoning_content + content)         │
│  • Artifact retrieval proxy                                     │
│  • Guardrails enforcement                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Competitor Containers                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ Baseline (ref)   │  │  Miner A         │  │   Miner B     │  │
│  │ CLI Agent +      │  │  Custom impl     │  │   Custom impl │  │
│  │ Sandbox          │  │                  │  │               │  │
│  └──────────────────┘  └──────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Platform Services                             │
│  • Web proxy/search APIs    • Sandbox API (Sandy)               │
│  • Vector DB/search         • Chutes inference proxy            │
└─────────────────────────────────────────────────────────────────┘
```

## Related Projects

| Project | Description |
|---------|-------------|
| [chutes-knowledge-agent](../chutes-knowledge-agent/) | UI and agent UX patterns reused in Janus |
| [chutes-bench-runner](https://chutes-bench-runner-ui.onrender.com) | Evaluation harness for running Janus benchmarks |
| [Squad API](https://github.com/chutesai/squad-api) | Inspiration for tooling (memory, sandboxes, tools) |
| [Sandy](../sandy/) | Sandbox-as-a-service (Firecracker VMs) |

## Notes

This repository is nested inside the Chutes monorepo but is intentionally **ignored** by the
monorepo `.gitignore`. It is meant to be managed as its own repo.
