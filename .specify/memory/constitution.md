# Janus PoC Constitution

> A spec-first Proof-of-Concept for the Janus platform - an AI agent gateway with OpenAI API compatibility.

## Version
1.0.4

## Ralph Wiggum Version
Installed from commit: 81231ca4e7466d84e3908841e9ed3d08e8c0803e

---

## Context Detection for AI Agents

This constitution is read by AI agents in two different contexts:

### 1. Interactive Mode
When the user is chatting with you outside of a Ralph loop:
- Be conversational and helpful
- Ask clarifying questions when needed
- Guide the user through decisions
- Help create specifications via `/speckit.specify`
- Discuss project ideas and architecture

### 2. Ralph Loop Mode
When you're running inside a Ralph bash loop (fed via stdin):
- Be fully autonomous — don't ask for permission
- Read IMPLEMENTATION_PLAN.md and pick the highest priority incomplete task
- Implement the task completely
- Run tests and verify acceptance criteria
- Commit and push (if Git Autonomy enabled)
- Output `<promise>DONE</promise>` ONLY when the task is 100% complete
- If criteria not met, fix issues and try again

**How to detect:** If the prompt instructs you to read IMPLEMENTATION_PLAN.md and pick a task, you're in Ralph Loop Mode.

---

## Parallel Ralph Loops & Port Conflicts

**Warning:** Multiple Ralph loops may run in parallel across different web dev projects on this machine. This can cause port conflicts, especially with Next.js dev servers.

**Common conflict scenarios:**
- Next.js defaults to port 3000
- Multiple projects competing for the same ports
- Background dev servers from other sessions

**Mitigation:**
- Use ports **4720+** for this project to reduce collision risk
- If a port is in use, pick another in the 4720-4799 range
- Check for running servers before starting: `lsof -i :PORT`
- Kill orphaned processes if needed: `kill $(lsof -t -i :PORT)`

**Recommended port assignments for janus-poc:**
- Next.js UI dev server: **4721**
- Gateway dev server: **4722**
- Test servers: **4723-4729**

---

## Core Principles

### I. Spec-First Development
All implementation follows the detailed specifications in `specs/`. Specs are the source of truth. Never implement features not covered by specs without explicit approval.

### II. OpenAI API Compatibility
The gateway MUST maintain compatibility with the OpenAI Chat Completions API. Clients should be able to use standard OpenAI SDKs.

### III. Simplicity & YAGNI
Build exactly what's needed, nothing more. No premature abstractions. No "just in case" features. The MVP scope in `specs/01_scope_mvp.md` defines what to build.

### IV. Autonomous Agent Development
AI coding agents work autonomously:
- Make decisions without asking for approval on details
- Commit and push changes (if Git Autonomy enabled)
- Test thoroughly before marking done
- Only ask when genuinely stuck

---

## Autonomous Working Standards

These principles apply to ALL agent sessions, not just Ralph loops.

### Full Autonomy Mode
- Work as autonomously as possible
- You have full trust and authority to make decisions
- Don't ask unnecessary questions
- Only come back when you've completed the task or are truly stuck
- Make informed decisions based on context
- Research extensively if needed (online, source code, third-party projects)

### Testing Requirements

**Time Budget:** Testing should consume **at most 25%** of total effort. Feature implementation should be **at least 75%** of agent time and tokens.

**Prioritize high-value tests:**
1. **Critical path smoke tests** — Does the app start? Do core endpoints respond?
2. **Integration tests for key flows** — Auth, chat completions, streaming
3. **Unit tests for complex logic** — Routing, parsing, validation

**Skip or defer:**
- Exhaustive edge case coverage
- Visual regression tests (unless UI is the spec focus)
- Tests for trivial CRUD or pass-through code

**Run test suites:**
```bash
# Unit + Integration tests
cd gateway && pytest
cd ui && npm test

# Type checking
cd gateway && mypy janus_gateway
cd ui && npm run typecheck
```

**Test hygiene:**
- Add tests for new functionality (keep it proportional)
- Update outdated tests
- Remove tests that no longer make sense
- All tests must pass before marking complete

**If testing is taking too long:** Stop, commit what works, note the gap in history.md, and move on. Don't let testing block feature delivery.

### Visual Testing

**Test the UI visually in browser:**
- Use Playwright (Claude Code), Browser MCP (Cursor), or Puppeteer MCP (Codex)
- Take screenshots on multiple viewports:
  - Desktop (1920x1080)
  - Tablet (768x1024)
  - Mobile (375x812)

**Check for:**
- No JavaScript console errors
- No failed network requests
- UI matches design system (Chutes style guide)
- No visual regressions
- Test functionality including authenticated areas

**If issues found:** Fix them and retest before marking complete.

### Commit & Push Protocol
- Commit all changes with clear, descriptive messages
- Push to remote
- Ensure nothing is left uncommitted
- Scope commits to the current project/task
- After commmits and pushes, if it's a Render hosted project, watche deploy on Render (via MCP) unt il successful (Florians Workspace, Id tea-cspqj3l6l47c739nvitg)

### Deploy & Verify

After every commit/push, deployment verification is **mandatory**:

**1. Watch Deployment via Render MCP**
- Use the Render MCP tools to monitor the deployment
- Call `list_services` to find the service IDs
- Call `list_deploys` to get the current deployment status
- Call `get_deploy` repeatedly until deployment completes
- Check `list_logs` if deployment fails to diagnose issues
- **Do NOT mark task complete until deployment succeeds**

**2. Test Backend on Production**
- Use API calls (via `curl` or similar) against the deployed gateway
- Test key endpoints: health check, chat completions, model listing
- Verify responses are correct and match expectations
- Check for error responses or unexpected behavior

**3. Test Frontend on Production**
- Use browser automation (Playwright MCP) to visit the deployed UI
- Navigate through key user flows
- Take screenshots to verify UI renders correctly
- Check browser console for JavaScript errors
- Verify API calls from frontend succeed

**4. Only Then Mark Complete**
- Deployment must be successful (not just pushed)
- Backend API tests must pass
- Frontend visual/functional tests must pass
- If any step fails, fix and redeploy before marking complete

### Documentation
Keep documentation up to date:
- **README.md**: Features, usage, setup instructions
- **INTERNAL.md** (if exists): Implementation details, infrastructure, secrets (gitignored)

Focus on information that future agents need but would lose when starting a new session.

Also update the history.md (create if missing) with the most relevant milestones and also note down there which specs you are working on.

### Completion Verification

Before marking any task complete, verify:
- [ ] All requirements met
- [ ] All tests passing (unit, integration, smoke)
- [ ] All edge cases handled
- [ ] Documentation updated
- [ ] No TODOs left incomplete
- [ ] Visual testing passed (if UI changes)
- [ ] Render deployment watched and succeeded (via Render MCP)
- [ ] Backend API tested on production
- [ ] Frontend tested in browser on production (if UI changes)

**Don't stop until the task is fully done.**

### Research When Needed
- Search online for solutions
- Read source code (project and third-party)
- Check past chat histories for similar examples
- Summarize findings before proceeding

### Local Environment Setup
For runtime configuration, API keys, and deployment credentials, refer to `credentials.md` in the project root. This file contains instructions for locating necessary values from local sources.

---

## Technical Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Gateway | FastAPI | Python 3.11 |
| UI | Next.js | Node 20+ |
| Testing (Python) | pytest | With pytest-asyncio |
| Testing (JS) | Vitest | For Next.js |
| API Contract | OpenAPI 3.1 | See specs/openapi/ |

---

## Project Structure

```
janus-poc/
├── gateway/           # FastAPI backend (Python 3.11)
│   └── janus_gateway/ # Main package
├── ui/                # Next.js frontend
├── specs/             # Implementation specifications
│   ├── openapi/       # OpenAPI schemas
│   ├── examples/      # Request/response examples
│   └── backlog/       # Future specs
├── scripts/           # Ralph loop scripts
└── .specify/          # Ralph Wiggum configuration
```

---

## Ralph Wiggum Configuration

### Autonomy Settings
- **YOLO Mode**: ENABLED
  - Claude Code: `--dangerously-skip-permissions`
  - Codex: `--dangerously-bypass-approvals-and-sandbox`
- **Git Autonomy**: ENABLED (auto-commit and push)

### Work Item Source
- **Source**: Existing Specs
- **Location**: `specs/` folder with numbered markdown files (00_xxx.md, 01_xxx.md, etc.)

### History Tracking (TODO: Implement)

The Ralph loop should maintain a history file to track progress and milestones:

**History File**: `.ralph/history.log`

**Format**:
```
[2025-01-23T10:15:00Z] STARTED spec: 41_enhanced_agent_system_prompt.md
[2025-01-23T10:45:00Z] COMPLETED spec: 41_enhanced_agent_system_prompt.md
[2025-01-23T10:45:05Z] STARTED spec: 42_sandbox_file_serving.md
...
```

**Log Events**:
- STARTED: When beginning work on a spec
- COMPLETED: When spec marked as COMPLETE
- FAILED: If spec implementation fails and needs retry
- MILESTONE: Major progress points within a spec

### Telegram Notifications

Send progress updates to Telegram for monitoring Ralph loop sessions.
Howto is described in ../affine/memory.md. there.
additionally send as audio as explained in 
/home/flori/Dev/chutes/.cursor/commands/notify-telegram-audio.md

**Environment Variables**:
```bash
TG_BOT_TOKEN="<bot-token>"  # Telegram bot token
TG_CHAT_ID="<chat-id>"      # Target chat for notifications
```

**Notification Triggers**:
1. **Session Start**: When Ralph loop begins
2. **Spec Completed**: When a spec is marked COMPLETE
3. **Session Summary**: Every N iterations (e.g., 5) or on completion

**Message Format**:
```
🤖 *Janus Ralph Loop Update*

✅ Recently Completed:
- Spec 41: Enhanced Agent System Prompt
- Spec 42: Sandbox File Serving

📋 Still Open (Next Up):
- Spec 43: Agent Sandbox Management
- Spec 44: Deep Research Integration
- Spec 45: Browser Automation

📊 Progress: 42/49 specs complete (86%)
```

**Implementation**:
```bash
# Send Telegram notification
curl -s -X POST "https://api.telegram.org/bot${TG_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TG_CHAT_ID}" \
  -d parse_mode="Markdown" \
  -d text="${MESSAGE}"
```

### Ralph Loop Scripts
Located in `scripts/`:
- `ralph-loop.sh` — Claude Code loop
- `ralph-loop-codex.sh` — OpenAI Codex loop

**Usage:**
```bash
# Planning: Create task list from specs
./scripts/ralph-loop.sh plan

# Building: Implement tasks one by one
./scripts/ralph-loop.sh        # Unlimited
./scripts/ralph-loop.sh 20     # Max 20 iterations
```

---

## Development Workflow

### Phase 1: Review Specifications

The specs are already written in `specs/`:
- `00_overview.md` - High-level project overview
- `01_scope_mvp.md` - MVP scope and boundaries
- `02_architecture.md` - System architecture
- ... and more

Each spec should be treated as a work item to implement.

### Phase 2: Run Planning Mode (Optional)

```bash
./scripts/ralph-loop.sh plan
```

This analyzes specs vs current code and creates IMPLEMENTATION_PLAN.md.

### Phase 3: Run Build Mode

```bash
./scripts/ralph-loop.sh
```

Each iteration:
1. Reads specs in numerical order
2. Picks the highest priority incomplete spec (or if that one seems to be unachievable or needs any of the other ones as a precondition, chooses that one instead)
3. Looks for a note in that spec about NR_OF_TRIES and increments it, if that note isn't found, adds it (at the very bottom). If NR_OF_TRIES already > 0 also look at history.md to understand what we struggled with or learnt alrady about it in previous tries. If NR_OF_TRIES=10 then we know this spec is unachievable (too hard or too big), so split it into simpler specs
4. Implements completely
5. Puts some notes about it into the history.md (e.g. lessons learned, but very concise). These notes can later help to understand what previous iterations did.
6. Runs tests
7. Verifies acceptance criteria
8. Commits and pushes
9. If commit triggered a deploy on render, watch deploy on Render via MCP until successful (fix and re-commit+push if needed, as often as needed)
10. Send two summaries about this iteration via telegram as explained in ../.cursor/commands/notify-telegram.md and ../.cursor/commands/notify-telegram-audio.md. Also send an image of a mermaid diagram (rendered) that explains what you built in the implementation of this spec.
11. Outputs `<promise>DONE</promise>` if successful
12. Exits for fresh context
13. Loop restarts

### Completion Signal Rules

- Output `<promise>DONE</promise>` ONLY when task acceptance criteria are 100% met
- The bash loop checks for this exact string
- If not found, the loop continues with another iteration
- This ensures tasks are truly complete before moving on

---

## Validation Commands

Run these after implementing:

```bash
# Gateway tests
cd gateway && pytest

# UI tests
cd ui && npm test

# Type checking
cd gateway && mypy janus_gateway
cd ui && npm run typecheck
```

---

## Governance

- **Amendments**: Update this file, increment version, note changes
- **Compliance**: Follow principles in spirit, not just letter
- **Exceptions**: Document and justify when deviating

---

## Pre-release Access

- If automating the frontend via Playwright (or similar), enter the pre-release
  password stored in `CHUTES_JANUS_PRE_RELEASE_PWD` into the pre-release modal
  before attempting any page interactions or API calls.

---

**Created**: 2025-01-22
**Version**: 1.0.4
**Amendments**:
- 1.0.2: Added explicit pre-release password entry guidance for browser automation.
- 1.0.3: Added parallel Ralph loops warning and port conflict mitigation (use ports 4720+).
- 1.0.4: Added testing time budget (max 25%) and prioritization guidance.
