# Claude Code Instructions

## Quick Start

**To start Ralph loop:**
```bash
./scripts/ralph-loop.sh
```

This works directly from specs — no planning step needed.

---

## How Ralph Works

1. Agent reads `specs/` folder
2. Picks the **highest priority incomplete spec** (lowest number first)
3. Implements it completely
4. Marks spec as `COMPLETE`
5. Outputs `<promise>DONE</promise>`
6. Loop restarts with fresh context
7. Repeat until all specs are done

---

## Project Constitution

Read `.specify/memory/constitution.md` for project principles.

---

## Spec Priority

Specs are numbered: `00_xxx.md`, `01_xxx.md`, etc.
- Lower number = higher priority
- Work on incomplete specs in order

---

## Project Structure

- `gateway/` - FastAPI backend (Python 3.11)
- `ui/` - Next.js frontend (Node 20+)
- `specs/` - Implementation specifications
- `scripts/` - Ralph loop automation

---

## Commands

### Planning Mode (Optional)
```bash
./scripts/ralph-loop.sh plan
```

### Build Mode
```bash
./scripts/ralph-loop.sh        # Unlimited iterations
./scripts/ralph-loop.sh 20     # Max 20 iterations
```

---

## Context Detection

When you're in **Ralph Loop Mode** (fed via stdin from the bash loop):
- Be fully autonomous
- Don't ask for permission
- Implement tasks completely
- Output `<promise>DONE</promise>` when done

When you're in **Interactive Mode** (chatting with user):
- Be conversational
- Ask clarifying questions
- Help with specs and planning
