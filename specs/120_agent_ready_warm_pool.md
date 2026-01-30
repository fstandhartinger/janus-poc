# Spec 120: Agent-Ready Warm Pool for Sandy

## Status: COMPLETE

## Priority: HIGH

## Context / Why

Based on research in spec 118, Sandy sandboxes need browser automation capabilities pre-installed for session injection to work. Currently, installing Playwright or agent-browser in a sandbox times out due to browser binary downloads. We need "Agent-Ready" sandboxes with everything pre-baked.

**Reference:** `docs/browser-user-session-pre-research.md` and `docs/browser-session-research-results.md`

## Goals

1. Create an Agent-Ready Sandy runtime image with browser automation tools
2. Enhance Sandy warm pool to support multiple flavors
3. Target <2s sandbox assignment with browser ready

## Non-Goals

- Session storage (that's spec 119)
- Session capture UI (that's spec 121)
- Session injection API (that's spec 122)

## Functional Requirements

### FR-1: Agent-Ready Runtime Image

Create a new Sandy runtime image variant:

```dockerfile
# sandy-runtime:agent-ready
FROM sandy-runtime:base

# Install Node.js tools
RUN npm install -g agent-browser
RUN agent-browser install

# Pre-download browser binaries
RUN playwright install chromium --with-deps

# Include CLI agents
RUN pip install claude-code codex aider-chat

# Set environment
ENV SANDY_AGENT_READY=1
ENV AGENT_BROWSER_INSTALLED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright
```

### FR-2: Warm Pool Flavors

Enhance `SANDY_PREWARM_COUNT` to support flavors:

```yaml
# Environment configuration
SANDY_PREWARM_COUNT=5                # Total warm sandboxes
SANDY_PREWARM_BASIC=3                # Basic (no browser)
SANDY_PREWARM_AGENT_READY=2          # Agent-Ready (with browser)
```

### FR-3: Sandbox Request with Flavor

Enhance `/api/sandboxes` endpoint:

```json
POST /api/sandboxes
{
  "flavor": "agent-ready",  // or "basic" (default)
  "enableVnc": true,
  "timeout": 300
}
```

### FR-4: Warm Pool Management

- Maintain separate pools for each flavor
- Refill pools when sandboxes are consumed
- Report pool status in `/api/health`

```json
GET /api/health
{
  "status": "ok",
  "warmPool": {
    "basic": { "available": 3, "target": 3 },
    "agent-ready": { "available": 1, "target": 2 }
  }
}
```

### FR-5: Agent-Ready Feature Detection

Sandboxes should report their capabilities:

```json
GET /api/sandboxes/{id}
{
  "sandboxId": "abc123",
  "flavor": "agent-ready",
  "capabilities": {
    "vnc": true,
    "browser": true,
    "agentBrowser": true,
    "playwright": true,
    "agents": ["claude-code", "codex", "aider"]
  }
}
```

## Technical Approach

### Sandy Changes

1. **SandboxPool class:**
   - Add flavor parameter to `get_sandbox()`
   - Maintain separate queues per flavor
   - Track pool metrics per flavor

2. **Runtime selection:**
   - Map flavor to runtime image tag
   - `basic` → `sandy-runtime:base`
   - `agent-ready` → `sandy-runtime:agent-ready`

3. **Pre-warming:**
   - Create sandboxes with correct runtime at startup
   - Background task refills pools

### Build Process

```bash
# Build agent-ready image
cd sandy/runtime
docker build -t sandy-runtime:agent-ready \
  --build-arg SANDY_ENABLE_PLAYWRIGHT=1 \
  --build-arg SANDY_ENABLE_AGENT_BROWSER=1 \
  .
```

## Acceptance Criteria

- [x] Agent-Ready runtime image built and tested (via `SANDY_ENABLE_PLAYWRIGHT=1` build arg)
- [x] Playwright works in Agent-Ready sandbox (built into runtime image)
- [x] Warm pool supports multiple flavors (SandboxPool with per-flavor queues)
- [x] `/api/sandboxes` accepts flavor parameter
- [x] Pool status reported in `/api/resources` endpoint with warmPool breakdown
- [x] Agent-Ready sandbox assignment <2s from pool (when pool is pre-warmed)
- [x] Documentation updated (README.md and build script)
- [x] Sandbox capabilities reported in `GET /api/sandboxes/{id}` response

## Performance Targets

| Metric | Target |
|--------|--------|
| Agent-Ready sandbox from pool | <2s |
| Agent-Ready sandbox cold start | <60s |
| Agent-browser first command | <3s |
| Profile loading | <1s |

## Testing

```bash
# Test agent-browser in Agent-Ready sandbox
curl -X POST https://sandy.../api/sandboxes \
  -d '{"flavor": "agent-ready", "enableVnc": true}'

# Execute agent-browser command
curl -X POST https://sandy.../api/sandboxes/{id}/exec \
  -d '{"command": "agent-browser --version"}'
```

## Notes

- Consider separate upstream workers for agent-ready
- May need larger worker instances (more RAM)
- Monitor startup times and optimize

---

*Reference: docs/browser-user-session-pre-research.md*
*Depends on: Spec 118 research results*
