# Janus PoC -- Architecture Overview

Janus is a competitive, OpenAI-compatible intelligence API where miners (competitors) submit Docker containers that expose a Chat Completions endpoint. The platform evaluates them on quality, speed, cost, streaming continuity, and multimodal handling. A composite score determines the leaderboard ranking.

Live at **[janus.rodeo](https://janus-ui.onrender.com)**.

---

## System Map

```mermaid
flowchart TB
    subgraph Clients
        UI["Chat UI<br/>(Next.js :3000)"]
        BENCH["Bench CLI<br/>(janus-bench)"]
        CURL["curl / SDK"]
    end

    subgraph Gateway["Janus Gateway :8000"]
        GW_CHAT["POST /v1/chat/completions"]
        GW_MODELS["GET /v1/models"]
        GW_ARENA["POST /v1/chat/completions/arena"]
        GW_ARTIFACTS["GET /v1/artifacts/:id"]
        GW_SEARCH["POST /api/search/web"]
        GW_RESEARCH["POST /api/research"]
        GW_SANDBOX["POST /api/sandbox/create"]
        REGISTRY["Competitor Registry"]
        STREAM["SSE Streaming<br/>+ Keep-alive"]
    end

    subgraph Competitors
        BASELINE_CLI["Baseline Agent CLI :8081<br/>(Sandy + CLI agents)"]
        BASELINE_LC["Baseline LangChain :8082<br/>(in-process tools)"]
        MINER_N["Miner N<br/>(custom container)"]
    end

    subgraph Platform["Platform Services"]
        SANDY["Sandy<br/>(Firecracker VMs)"]
        CHUTES["Chutes Inference<br/>(LLM, Image, TTS, Video)"]
        MEMORY["Memory Service :8090"]
        SCORING["Scoring Service :8100"]
        SEARCH_SVC["chutes-search"]
        BROWSER_SVC["Browser Session Service"]
    end

    UI --> GW_CHAT
    BENCH --> GW_CHAT
    CURL --> GW_CHAT
    UI --> GW_MODELS
    UI --> GW_ARENA
    UI --> GW_ARTIFACTS

    GW_CHAT --> REGISTRY
    REGISTRY --> BASELINE_CLI
    REGISTRY --> BASELINE_LC
    REGISTRY --> MINER_N

    BASELINE_CLI --> SANDY
    BASELINE_CLI --> CHUTES
    BASELINE_CLI --> MEMORY
    BASELINE_CLI --> SEARCH_SVC
    BASELINE_LC --> CHUTES
    BASELINE_LC --> SEARCH_SVC

    SANDY --> CHUTES
    SCORING --> BENCH

    BASELINE_CLI -.->|SSE stream| STREAM
    BASELINE_LC -.->|SSE stream| STREAM
    STREAM -.->|forwarded| UI
```

---

## Core Data Flow

Every request follows the same path regardless of client:

```
Client --> Gateway --> Competitor --> [Sandy / LLM] --> SSE stream back
```

1. **Client** sends an OpenAI-compatible `POST /v1/chat/completions` request.
2. **Gateway** resolves the target competitor via the registry (explicit `competitor_id`, model name match, or default).
3. **Gateway** proxies the request to the competitor's `/v1/chat/completions` endpoint.
4. **Competitor** decides internally whether the request is simple (fast path -- direct LLM) or complex (agent path -- Sandy sandbox with CLI agent).
5. **Competitor** streams SSE chunks back, including `reasoning_content` for intermediate steps and `content` for the final answer.
6. **Gateway** transparently forwards every SSE chunk, injecting keep-alive pings on idle intervals.
7. **Client** renders tokens incrementally.

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant R as Registry
    participant B as Competitor
    participant S as Sandy

    C->>G: POST /v1/chat/completions
    G->>R: resolve competitor
    R-->>G: competitor URL
    G->>B: forward request

    alt Fast Path
        B->>B: Direct LLM call
        B-->>G: SSE (content tokens)
    else Agent Path
        B->>S: Create sandbox + run agent
        S-->>B: Agent output stream
        B-->>G: SSE (reasoning_content, content, artifacts)
    end

    G-->>C: SSE pass-through
    G-->>C: data: [DONE]
```

---

## OpenAI Chat Completions API Compatibility

The gateway and all competitors implement the standard OpenAI Chat Completions API with the following extensions:

| Standard OpenAI | Janus Extension |
|-----------------|-----------------|
| `delta.content` | `delta.reasoning_content` -- intermediate thinking / tool traces |
| `usage.prompt_tokens` | `usage.cost_usd` -- estimated USD cost |
| `usage.completion_tokens` | `usage.sandbox_seconds` -- sandbox execution time |
| -- | `artifacts[]` array on response chunks |
| -- | `metadata.routing_decision` -- pin routing path and model |
| -- | `generation_flags` -- request image/video/audio/research generation |
| -- | `debug: true` -- enable debug trace events |
| -- | `competitor_id` -- explicit competitor routing |

All streaming uses Server-Sent Events (SSE) with the standard `data: {json}\n\n` format and `data: [DONE]\n\n` termination.

---

## Component Boundaries

```mermaid
flowchart LR
    subgraph "Frontend (Node 20)"
        UI["Chat UI"]
    end

    subgraph "Gateway (Python 3.11)"
        GW["Gateway API"]
    end

    subgraph "Competitors (Python 3.11)"
        B1["Baseline CLI Agent"]
        B2["Baseline LangChain"]
    end

    subgraph "Supporting Services"
        MEM["Memory Service"]
        SCORE["Scoring Service"]
        BSESS["Browser Session Service"]
    end

    subgraph "External"
        SANDY["Sandy (VMs)"]
        CHUTES["Chutes AI APIs"]
        SERPER["Serper / SearXNG"]
    end

    UI -->|HTTP + SSE| GW
    GW -->|HTTP + SSE| B1
    GW -->|HTTP + SSE| B2
    GW -->|REST| MEM
    GW -->|REST| SCORE
    GW -->|REST| BSESS
    GW -->|REST| SANDY

    B1 -->|REST + SSE| SANDY
    B1 -->|REST| CHUTES
    B2 -->|REST| CHUTES
    GW -->|REST| SERPER
```

### Component Summary

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| **Chat UI** | Next.js 14, Zustand, Tailwind | 3000 | ChatGPT-style frontend with SSE streaming, reasoning traces, artifacts, arena mode |
| **Gateway** | FastAPI, httpx, structlog | 8000 | OpenAI-compatible proxy, competitor routing, artifact storage, web search, transcription |
| **Baseline Agent CLI** | FastAPI, Sandy SDK | 8081 | Reference competitor: dual-path routing, CLI agents in Firecracker VMs |
| **Baseline LangChain** | FastAPI, LangChain | 8082 | Alternative competitor: in-process LangChain tools agent |
| **Bench** | CLI (Click), httpx | -- | Benchmark runner measuring quality, speed, cost, streaming, multimodal |
| **Scoring Service** | FastAPI, SQLAlchemy | 8100 | Executes benchmark suites, stores results, provides leaderboard |
| **Memory Service** | FastAPI, PostgreSQL | 8090 | Memory extraction and context recall across sessions |
| **Browser Session Service** | FastAPI | -- | Secure browser session storage for authenticated browsing |

---

## Deployment Topology

### Local Development

All services run on localhost with distinct ports:

```mermaid
flowchart LR
    subgraph localhost
        UI["UI :3000"]
        GW["Gateway :8000"]
        B1["Baseline CLI :8081"]
        B2["Baseline LangChain :8082"]
        SCORE["Scoring :8100"]
        MEM["Memory :8090"]
    end

    subgraph External
        SANDY["Sandy<br/>(remote)"]
        CHUTES["Chutes AI"]
    end

    UI --> GW
    GW --> B1
    GW --> B2
    GW --> MEM
    GW --> SCORE
    B1 --> SANDY
    B1 --> CHUTES
    B2 --> CHUTES
```

```bash
# Terminal 1: Gateway
cd gateway && python -m janus_gateway.main

# Terminal 2: Baseline CLI Agent
cd baseline-agent-cli && python -m janus_baseline_agent_cli.main

# Terminal 3: Baseline LangChain (optional)
cd baseline-langchain && python -m janus_baseline_langchain.main

# Terminal 4: Chat UI
cd ui && npm run dev
```

### Production (Render)

Deployed via `render.yaml` as separate web services in the Oregon region:

```mermaid
flowchart TB
    subgraph Render["Render Platform"]
        UI_R["janus-ui<br/>(Node, free)"]
        GW_R["janus-gateway<br/>(Python, free)"]
        B1_R["janus-baseline-agent<br/>(Python, starter)"]
        B2_R["janus-baseline-langchain<br/>(Python, free)"]
        SC_R["janus-scoring-service<br/>(Python, starter)"]
        MEM_R["janus-memory-service<br/>(Python, free)"]
        BS_R["janus-browser-session-service<br/>(Python, free)"]
    end

    subgraph External["External Services"]
        SANDY_R["Sandy VMs"]
        CHUTES_R["Chutes Inference"]
    end

    UI_R --> GW_R
    GW_R --> B1_R
    GW_R --> B2_R
    GW_R --> MEM_R
    GW_R --> SC_R
    B1_R --> SANDY_R
    B1_R --> CHUTES_R
    B2_R --> CHUTES_R
    SC_R --> SANDY_R
```

| Service | Render URL | Plan |
|---------|-----------|------|
| Chat UI | https://janus-ui.onrender.com | free |
| Gateway | https://janus-gateway-bqou.onrender.com | free |
| Baseline Agent | https://janus-baseline-agent.onrender.com | starter |
| Baseline LangChain | https://janus-baseline-langchain.onrender.com | free |
| Scoring Service | https://janus-scoring-service.onrender.com | starter |
| Memory Service | https://janus-memory-service.onrender.com | free |

The baseline agent uses the "starter" plan because it handles long-running Sandy sandbox sessions that require more compute and longer timeouts.

---

## The Competition Model

Janus is both a competition and a product:

1. **Miners/Competitors** submit Docker containers exposing the OpenAI Chat Completions API.
2. Containers can implement any strategy: CLI agents, n8n workflows, multi-model chains, RAG pipelines, or custom logic.
3. The platform enforces the API contract, continuous streaming, and guardrails.
4. A **composite score** across five dimensions determines rankings:
   - Quality (40%) -- response correctness
   - Speed (20%) -- TTFT and throughput
   - Cost (15%) -- token and sandbox efficiency
   - Streaming (15%) -- continuity and gap metrics
   - Multimodal (10%) -- image/vision/media handling
5. The best implementations earn rewards.

```mermaid
flowchart TD
    subgraph Submission
        DOCKER["Docker Container<br/>exposes /v1/chat/completions"]
    end

    subgraph Evaluation
        BENCH["Benchmark Runner"]
        QUALITY["Quality<br/>40%"]
        SPEED["Speed<br/>20%"]
        COST["Cost<br/>15%"]
        STREAMING["Streaming<br/>15%"]
        MULTIMODAL["Multimodal<br/>10%"]
    end

    subgraph Result
        COMPOSITE["Composite Score<br/>(0-100)"]
        LEADER["Leaderboard"]
    end

    DOCKER --> BENCH
    BENCH --> QUALITY
    BENCH --> SPEED
    BENCH --> COST
    BENCH --> STREAMING
    BENCH --> MULTIMODAL
    QUALITY --> COMPOSITE
    SPEED --> COMPOSITE
    COST --> COMPOSITE
    STREAMING --> COMPOSITE
    MULTIMODAL --> COMPOSITE
    COMPOSITE --> LEADER
```

---

## Key Design Decisions

1. **OpenAI API as the universal contract** -- competitors only need to implement `/v1/chat/completions` with SSE streaming. This makes any OpenAI-compatible service a potential competitor.

2. **Gateway is a thin proxy** -- the gateway does not process or transform AI content. It resolves the competitor, forwards the request, relays SSE chunks with keep-alives, and stores artifacts. All intelligence lives in the competitors.

3. **Dual-path architecture in the reference baseline** -- simple questions hit fast LLMs directly (sub-second); complex tasks spin up a full Sandy sandbox with a CLI agent (Claude Code, Aider). This demonstrates the power of the "anything in, anything out" approach.

4. **Continuous streaming is mandatory** -- competitors must produce SSE events continuously. Keep-alive pings (`": ping\n\n"`) bridge idle periods. The benchmark measures streaming gaps and penalizes stalls.

5. **Sandbox isolation via Sandy** -- complex tasks run in Firecracker micro-VMs with full Linux environments. Agents have shell access, package installation, browser automation, and file creation -- all safely isolated.
