# Specification: Sandy Cross-Repo Integration Map

## Status: COMPLETE

## Feature: Sandy Compatibility Across Chutes Projects

### Overview
Multiple Chutes repositories rely on Sandy as the sandbox/agent execution substrate. We
need a single, up-to-date map of how each repo integrates with Sandy (endpoints, env vars,
and expectations), and a small set of compatibility rules to prevent silent breakage.

This spec is primarily documentation + verification, but may require code changes if
inconsistencies or regressions are found.

### Test-First Validation (Do Before Implementing Anything)
1. Verify Sandy server exposes the expected endpoints (create/exec/files/terminate/agent-run).
2. In each dependent repo, confirm:
   - The Sandy base URL + API key configuration are consistent
   - Client code calls the correct endpoints and handles transient failures
   - Agent-run flows pass router configuration when using "janus-router"
3. Only implement changes if any criterion fails.

### User Stories
- As a platform engineer, I want Sandy clients across repos to stay compatible so that
  agentic features don’t break when Sandy evolves.
- As a developer, I want a clear integration map so I can debug failures quickly.

---

## Functional Requirements

### FR-1: Sandy Endpoint Contract Is Documented
Document the authoritative Sandy API endpoints used by products.

**Acceptance Criteria:**
- [x] The documented endpoint list matches the Sandy server implementation.
- [x] The map includes both exec-based workflows and the streaming `/agent/run` workflow.

### FR-2: Cross-Repo Integration Map Exists (Concrete File References)
Identify the integration points in each dependent repo and the purpose of the integration.

**Acceptance Criteria:**
- [x] The map includes at least these repos and file-level entry points:
  - `../sandy` (server)
  - `janus-poc` (baseline CLI agent + UI)
  - `../chutes-search`
  - `../chutes-bench-runner`
  - `../agent-as-a-service-web`
  - `../chutes-webcoder`
- [x] For each repo, the map lists:
  - Base URL env var(s)
  - API key env var(s)
  - Which Sandy endpoints are called
  - Any special flags (priority, preemptable, flavor, docker socket, browser/VNC)

#### Integration Map (Current File References)

**Sandy server**
- Code:
  - `../sandy/sandy/app.py` (authoritative worker API)
  - `../sandy/sandy/controller.py` (controller/proxy API)
- Endpoints verified in `app.py` and controller proxy:
  - `POST /api/sandboxes`
  - `GET /api/sandboxes/{id}`
  - `GET /api/sandboxes/{id}/vnc`
  - `POST /api/sandboxes/{id}/preview`
  - `POST /api/sandboxes/{id}/exec`
  - `POST /api/sandboxes/{id}/agent/run`
  - `POST /api/sandboxes/{id}/agent/cancel`
  - `POST /api/sandboxes/{id}/files/write`
  - `GET /api/sandboxes/{id}/files/read`
  - `GET /api/sandboxes/{id}/files/list`
  - `POST /api/sandboxes/{id}/terminate`
  - `POST /api/sandboxes/{id}/refresh`
- Policy notes: worker supports priority/preemptable sandboxes, agent-ready execution, file I/O,
  preview/VNC, and termination. Controller forwards the same core sandbox route family.

**Janus PoC (this repo)**
- Baseline CLI agent Sandy client:
  - `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py`
  - Env: `SANDY_BASE_URL`, `SANDY_API_KEY`
  - Router for agent-run: `BASELINE_AGENT_CLI_PUBLIC_ROUTER_URL` (or local router host/port)
  - Endpoints: create, exec, files/write, files/read, terminate, streaming agent/run
  - Policy: sends `apiBaseUrl` to Sandy when using the Janus router; for Claude Code agent-run it
    sends the Janus system prompt inline and removes `JANUS_SYSTEM_PROMPT_PATH` to avoid
    conflicting `--append-system-prompt` and `--append-system-prompt-file` flags.
  - Retry/timeout policy: `sandy_agent_timeout`, `http_client_timeout`, SSE keepalives, and
    `_run_agent_via_api_with_retry` retry timeout failures with user-visible retry events.
- UI artifact caching/serving (consumes artifact URLs produced by Sandy workloads):
  - `ui/src/app/api/artifacts/cache/route.ts`
  - `ui/src/app/api/artifacts/[...path]/route.ts`

**chutes-search**
- Sandy client: `../chutes-search/src/lib/sandy.ts`
- Typical use: agent-ready sandboxes for deep research + browser automation
- Key consumer: `../chutes-search/src/lib/search/deepResearchCollector.ts`
- Env: `SANDY_BASE_URL`, `SANDY_API_KEY`
- Endpoints: create, status, exec, files/write, files/read, files/list, terminate
- Special flags: creates `priority: 1`, `preemptable: false`, `flavor: agent-ready`
- Retry/timeout policy: `DEFAULT_TIMEOUT_MS`, `DEFAULT_RETRY_COUNT`, exponential backoff, retries
  5xx/429/upstream errors, and per-exec timeout padding.
- Router policy: `deepResearchCollector.ts` selects `janus-router` only when
  `SANDY_AGENT_API_BASE_URL`, `SANDY_AGENT_ROUTER_URL`, or `JANUS_ROUTER_URL` is configured.

**chutes-bench-runner**
- Sandy client: `../chutes-bench-runner/backend/app/services/sandy_service.py`
- Config: `../chutes-bench-runner/backend/app/core/config.py` (base URL + API key)
- Typical use: low-priority, preemptable sandboxes for benchmark execution
- Env/config: `sandy_base_url`, `sandy_api_key`, optional `sandy_docker_upstream`
- Endpoints: create, exec, files/write, terminate, stats, resource/metrics reads, streaming
  agent/run for agent-backed benchmarks
- Special flags: `priority: 3`, `preemptable: true` by default; `enableDockerSocket`; optional
  upstream override when Docker socket or agent support is required.
- Retry/timeout policy: pooled `httpx.AsyncClient`, retries create/exec/write/terminate on
  transient 408/429/5xx, retries agent warmup failures, and uses explicit request timeouts.

**agent-as-a-service-web**
- Ops console frontend uses Sandy agent-run and optionally a router base:
  - `../agent-as-a-service-web/script.js`
- Config: `data-ops-api-base`, `data-ops-router-base`, local settings `agent_ops_router_base`
- Endpoints: create, exec, files/list, files/read, files/write, preview, stats, terminate,
  streaming agent/run, agent/cancel
- Special flags: UI exposes priority, preemptable, docker socket, browser/VNC, upstream selection.
- Router policy: agent-run now fails fast with a clear "Model Auto Router requires a router API
  base URL." message when `janus-router` is selected without a router base.
- Retry/timeout policy: auth fetch retries once after refresh for 401/403; Sandy operation errors
  are surfaced from response bodies instead of generic "Unknown error" messages.

**chutes-webcoder**
- Sandy agent-run proxy route:
  - `../chutes-webcoder/app/api/agent-run/route.ts`
  - Env: `SANDY_BASE_URL`, `SANDY_API_KEY`, and router base env vars for "janus-router"
- Sandy proxy helpers:
  - `../chutes-webcoder/lib/server/sandy-proxy.ts`
- Endpoints: streaming agent/run proxy and sandbox host proxy requests via `proxySandyRequest`
- Router policy: fails fast with HTTP 400 when model `janus-router` lacks
  `SANDY_AGENT_API_BASE_URL` or a request `apiBaseUrl`.
- Retry/timeout policy: agent-run configures an `undici.Agent` with duration-based connect,
  headers, and body timeouts; create-sandbox flow has transient retry handling.

### FR-3: Router Usage Is Consistent for Agent-Run
When running CLI agents via Sandy `/agent/run` with model "janus-router", the caller must
provide an API base URL for the router (or explicitly disable router usage).

**Acceptance Criteria:**
- [x] Agent-run callers provide a router API base when using "janus-router", or fail fast with a
  clear configuration error.
- [x] No client passes conflicting system prompt flags to Claude Code wrappers.

### FR-4: Failure Modes Are Documented + Handled
Transient Sandy failures (502/503, agent warmup, timeouts) should be retried where
appropriate, and surfaced clearly to users.

**Acceptance Criteria:**
- [x] Each repo’s Sandy client documents its retry/timeout policy.
- [x] User-facing apps avoid vague failures (e.g., "Unknown error") when Sandy is unavailable.

---

## Success Criteria
- A developer can quickly answer: "Which repo calls which Sandy endpoint and why?"
- Sandy changes can be rolled out without breaking downstream products.

---

## Dependencies
- Sandy server implementation in `../sandy`
- Downstream Sandy clients in the repos listed above

## Assumptions
- Repos are colocated under `/home/flori/Dev/chutes/` (or similar), allowing cross-repo searching.

---

## Completion Signal

### Implementation Checklist
- [x] Add/refresh a cross-repo Sandy integration map in this spec (file references + env vars).
- [x] Verify endpoints exist in Sandy server and match documentation.
- [x] Verify each client’s endpoint usage and retry behavior.
- [x] Implement fixes in downstream repos if verification fails.

### Testing Requirements

The agent MUST complete ALL before outputting the magic phrase:

#### Verification
- [x] All acceptance criteria verified
- [x] Cross-repo references validated via `rg`/file reads (no stale links)

#### Regression Guard
- [x] Add at least one automated check or lightweight test in the most failure-prone integration
  (where feasible) to prevent reintroducing known breakages.

### Verification Report (2026-04-26)

- Verified Sandy worker/controller route decorators with `rg` and added
  `tests/integration/test_sandy_cross_repo_contract.py` to keep the route contract, file
  references, router-base policy, Claude Code prompt safety, and retry/timeout assumptions checked.
- Fixed `../agent-as-a-service-web/script.js`: the advanced agent-run flow now reads `routerBase`
  from config and both agent-run flows fail fast when `janus-router` is selected without a router
  API base.
- Verified Janus baseline CLI already sends router `apiBaseUrl` for Sandy agent-run and avoids the
  Claude Code conflicting system prompt path by sending inline `systemPrompt`.
- Verified `../chutes-webcoder/app/api/agent-run/route.ts` already fails fast for `janus-router`
  without an API base.

### Iteration Instructions
If ANY check fails:
1. Identify the specific inconsistency or regression
2. Fix the relevant repo(s)
3. Re-verify the map and acceptance criteria
4. Commit and push
5. Check again

**Only when ALL checks pass, output:** `<promise>DONE</promise>`
