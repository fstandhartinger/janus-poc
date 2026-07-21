# Janus PoC

> **Sandy dependency**: This project uses Sandy on the production servers (new\_sandy / old\_sandy). Do NOT deploy Sandy changes to bench-runner-sandy (`88.99.58.39`), which is dedicated to `chutes-bench-runner`. Do NOT change Sandy server configs (systemd overrides, autoscaler limits, resource watermarks) on Hetzner servers to accommodate this project — doing so has previously broken `chutes-bench-runner` throughput (incident 2026-03-13). Use a separate Sandy instance or test changes in isolation first.

**[janus.rodeo](https://janus.rodeo)** — A competitive, OpenAI-compatible intelligence API where miners compete to build the best universal agent. Anything in, anything out.

> *Janus* is the Roman god of beginnings, transitions, and duality — looking to the past and future simultaneously. Here, Janus rides the bull: a nod to the crypto-bullish ethos and the rodeo-style miner competition.

## Live Deployment

| Service | URL | Status |
|---------|-----|--------|
| **Janus UI** | https://janus.rodeo (also https://janus-ui.onrender.com) | live |
| **Janus Gateway** | https://janus-gateway-bqou.onrender.com | live |
| **Janus Baseline Agent** | https://janus-baseline-agent.onrender.com | live |
| **Janus Browser Session Service** | https://janus-browser-session-service.onrender.com | live |
| **Janus Baseline LangChain** | https://janus-baseline-langchain.onrender.com | **suspended** |
| **Janus Scoring Service** | https://janus-scoring-service.onrender.com | **suspended** |
| **Janus Memory Service** | https://janus-memory-service.onrender.com | **suspended** |

> **Suspended services (2026-07):** Render team workspaces no longer have a free
> tier, so janus-baseline-langchain, janus-scoring-service and
> janus-memory-service are suspended. The app degrades gracefully without them:
> the langchain competitor is not offered (BASELINE_LANGCHAIN_URL unset), the
> scoring pages show an "offline" banner, and memory features report themselves
> unavailable. Chat, routing, image generation, TTS/STT and auth all work
> without them.
>
> **Model ids rotate:** the Chutes catalog changes over time. If chat suddenly
> answers "I encountered an error", first verify every model id in
> `baseline-agent-cli/janus_baseline_agent_cli/routing.py` (and the
> `BASELINE_MODEL` env var on Render) against
> `GET https://llm.chutes.ai/v1/models`, and probe the image/STT chute
> endpoints in `services/direct_image.py` and the gateway `whisper_endpoint`.

## Components

| Component | Description | Local Port |
|-----------|-------------|------------|
| [Gateway](gateway/) | OpenAI-compatible proxy and routing | 8000 |
| [Chat UI](ui/) | Next.js frontend with landing, chat, competition & marketplace pages | 3000 |
| [Baseline Agent CLI](baseline-agent-cli/) | Reference competitor implementation | 8081 |
| [Baseline LangChain](baseline-langchain/) | LangChain-based baseline competitor | 8082 |
| [Bench](bench/) | Evaluation harness and scoring | CLI |
| [Scoring Service](scoring-service/) | Benchmark scoring backend | 8100 |
| [Memory Service](memory-service/) | Memory extraction and retrieval backend | 8090 |

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
BASELINE_AGENT_CLI_PORT=8081 python -m janus_baseline_agent_cli.main

# Terminal 3 (optional): Baseline LangChain
cd baseline-langchain
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
BASELINE_LANGCHAIN_PORT=8082 python -m janus_baseline_langchain.main

# Terminal 4: Chat UI
cd ui
npm install
npm run dev

# Terminal 5: Scoring Service (optional)
cd scoring-service
python -m venv .venv && source .venv/bin/activate
pip install -e "../bench"
pip install -r requirements.txt
uvicorn scoring_service.main:app --reload --port 8100

# Terminal 6: Memory Service (optional)
cd memory-service
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/memory_db MEMORY_INIT_DB=true uvicorn memory_service.main:app --reload --port 8090
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
- [API Docs](https://janus-ui.onrender.com/api-docs) - Janus API reference, examples, and extensions
- [Swagger UI](https://janus-gateway-bqou.onrender.com/api/docs) - Interactive OpenAPI explorer

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
| Scoring Service | Unit/Integration | `cd scoring-service && pytest` |
| UI | UI | `cd ui && npm test` |
| End-to-end | Smoke | Run gateway + baseline + UI and verify `/health` + a chat request |

```bash
# Comprehensive test runner
./scripts/run-tests.sh local

# Unit test runner
./scripts/run-unit-tests.sh

# Gateway tests
cd gateway && pytest

# Baseline tests
cd baseline-agent-cli && pytest

# Baseline LangChain tests
cd baseline-langchain && pytest

# Benchmark runner tests
cd bench && pytest

# Scoring service tests
cd scoring-service && pytest

# UI tests
cd ui && npm test
```

The shared tests in `tests/` honor `TEST_MODE` (`local`, `deployed`, `both`) and
`TEST_*_URL` overrides. Visual screenshots land in `./test-screenshots/`.

## Environment Variables

See individual component READMEs for full configuration:

| Variable | Description |
|----------|-------------|
| `JANUS_PORT` | Gateway port (default: 8000) |
| `BASELINE_AGENT_CLI_PORT` | Baseline agent CLI port (default: 8080) |
| `BASELINE_LANGCHAIN_PORT` | Baseline LangChain port (default: 8080) |
| `NEXT_PUBLIC_GATEWAY_URL` | Gateway URL for UI |
| `NEXT_PUBLIC_ENABLE_VOICE_INPUT` | Toggle voice input in the UI |
| `CHUTES_OAUTH_CLIENT_ID` | Chutes OAuth client ID for UI sign-in |
| `CHUTES_OAUTH_CLIENT_SECRET` | Chutes OAuth client secret for UI sign-in |
| `CHUTES_OAUTH_REDIRECT_URI` | OAuth redirect URI for UI sign-in |
| `CHUTES_OAUTH_COOKIE_SECRET` | Optional secret for encrypting OAuth cookies |
| `CHUTES_API_KEY` | Chutes Whisper API key for transcription |
| `SERPER_API_KEY` | Serper API key for web search |
| `SEARXNG_API_URL` | SearXNG base URL for web search fallback |
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
├── scoring-service/  # Scoring service backend
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
| [Model Router](../model-router/README.md) | Standalone intelligent LLM request router (extracted from Janus). Classifies requests and routes to the best model per task type. Both baselines embed a local copy of this router. |
| [chutes-knowledge-agent](../chutes-knowledge-agent/) | UI and agent UX patterns reused in Janus |
| [chutes-bench-runner](https://chutes-bench-runner-ui.onrender.com) | Evaluation harness for running Janus benchmarks |
| [Squad API](https://github.com/chutesai/squad-api) | Inspiration for tooling (memory, sandboxes, tools) |
| [Sandy](../sandy/) | Sandbox-as-a-service (Firecracker VMs) |

## Notes

This repository is nested inside the Chutes monorepo but is intentionally **ignored** by the
monorepo `.gitignore`. It is meant to be managed as its own repo.
