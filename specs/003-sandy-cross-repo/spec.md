# Specification: Sandy Cross-Repo Integration Map

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
- [ ] The documented endpoint list matches the Sandy server implementation.
- [ ] The map includes both exec-based workflows and the streaming `/agent/run` workflow.

### FR-2: Cross-Repo Integration Map Exists (Concrete File References)
Identify the integration points in each dependent repo and the purpose of the integration.

**Acceptance Criteria:**
- [ ] The map includes at least these repos and file-level entry points:
  - `../sandy` (server)
  - `janus-poc` (baseline CLI agent + UI)
  - `../chutes-search`
  - `../chutes-bench-runner`
  - `../agent-as-a-service-web`
  - `../chutes-webcoder`
- [ ] For each repo, the map lists:
  - Base URL env var(s)
  - API key env var(s)
  - Which Sandy endpoints are called
  - Any special flags (priority, preemptable, flavor, docker socket, browser/VNC)

#### Integration Map (Current File References)

**Sandy server**
- Code: `../sandy/sandy/app.py`
- Endpoints (non-exhaustive):
  - `POST /api/sandboxes`
  - `POST /api/sandboxes/{id}/exec`
  - `POST /api/sandboxes/{id}/agent/run`
  - `POST /api/sandboxes/{id}/files/write`
  - `GET /api/sandboxes/{id}/files/read`
  - `GET /api/sandboxes/{id}/files/list`
  - `POST /api/sandboxes/{id}/terminate`

**Janus PoC (this repo)**
- Baseline CLI agent Sandy client:
  - `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py`
  - Env: `SANDY_BASE_URL`, `SANDY_API_KEY`
  - Router for agent-run: `BASELINE_AGENT_CLI_PUBLIC_ROUTER_URL` (or local router host/port)
- UI artifact caching/serving (consumes artifact URLs produced by Sandy workloads):
  - `ui/src/app/api/artifacts/cache/route.ts`
  - `ui/src/app/api/artifacts/[...path]/route.ts`

**chutes-search**
- Sandy client: `../chutes-search/src/lib/sandy.ts`
- Typical use: agent-ready sandboxes for deep research + browser automation
- Key consumer: `../chutes-search/src/lib/search/deepResearchCollector.ts`

**chutes-bench-runner**
- Sandy client: `../chutes-bench-runner/backend/app/services/sandy_service.py`
- Config: `../chutes-bench-runner/backend/app/core/config.py` (base URL + API key)
- Typical use: low-priority, preemptable sandboxes for benchmark execution

**agent-as-a-service-web**
- Ops console frontend uses Sandy agent-run and optionally a router base:
  - `../agent-as-a-service-web/script.js`

**chutes-webcoder**
- Sandy agent-run proxy route:
  - `../chutes-webcoder/app/api/agent-run/route.ts`
  - Env: `SANDY_BASE_URL`, `SANDY_API_KEY`, and router base env vars for "janus-router"
- Sandy proxy helpers:
  - `../chutes-webcoder/lib/server/sandy-proxy.ts`

### FR-3: Router Usage Is Consistent for Agent-Run
When running CLI agents via Sandy `/agent/run` with model "janus-router", the caller must
provide an API base URL for the router (or explicitly disable router usage).

**Acceptance Criteria:**
- [ ] Agent-run callers provide a router API base when using "janus-router", or fail fast with a
  clear configuration error.
- [ ] No client passes conflicting system prompt flags to Claude Code wrappers.

### FR-4: Failure Modes Are Documented + Handled
Transient Sandy failures (502/503, agent warmup, timeouts) should be retried where
appropriate, and surfaced clearly to users.

**Acceptance Criteria:**
- [ ] Each repo’s Sandy client documents its retry/timeout policy.
- [ ] User-facing apps avoid vague failures (e.g., "Unknown error") when Sandy is unavailable.

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
- [ ] Add/refresh a cross-repo Sandy integration map in this spec (file references + env vars).
- [ ] Verify endpoints exist in Sandy server and match documentation.
- [ ] Verify each client’s endpoint usage and retry behavior.
- [ ] Implement fixes in downstream repos if verification fails.

### Testing Requirements

The agent MUST complete ALL before outputting the magic phrase:

#### Verification
- [ ] All acceptance criteria verified
- [ ] Cross-repo references validated via `rg`/file reads (no stale links)

#### Regression Guard
- [ ] Add at least one automated check or lightweight test in the most failure-prone integration
  (where feasible) to prevent reintroducing known breakages.

### Iteration Instructions
If ANY check fails:
1. Identify the specific inconsistency or regression
2. Fix the relevant repo(s)
3. Re-verify the map and acceptance criteria
4. Commit and push
5. Check again

**Only when ALL checks pass, output:** `<promise>DONE</promise>`
