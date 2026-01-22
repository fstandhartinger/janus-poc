# Janus PoC Constitution

> A spec-first Proof-of-Concept for the Janus platform - an AI agent gateway with OpenAI API compatibility.

## Version
1.0.0

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
2. Picks the highest priority incomplete spec
3. Implements completely
4. Runs tests
5. Verifies acceptance criteria
6. Commits and pushes
7. Outputs `<promise>DONE</promise>` if successful
8. Exits for fresh context
9. Loop restarts

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

**Created**: 2025-01-22
**Version**: 1.0.0
