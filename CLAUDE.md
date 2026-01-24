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
- Still work autonomously when given tasks
- Only ask when genuinely stuck or need clarification
- Make informed decisions based on context

---

## Autonomous Working Standards

**These apply to ALL sessions, not just Ralph loops.**

### Full Autonomy
- Work autonomously — you have full trust and authority
- Don't ask unnecessary questions
- Research extensively if needed (online, source code, third-party projects)
- Only come back when task is complete or you're truly stuck

### Testing (Required)
```bash
# Run all tests
cd gateway && pytest
cd ui && npm test

# Type checking
cd gateway && mypy janus_gateway
cd ui && npm run typecheck
```
- Add tests for new functionality
- Update/remove outdated tests
- **All tests must pass before marking complete**

### Visual Testing (For UI Changes)
- Use Playwright MCP to test in browser
- Screenshot on Desktop (1920x1080), Tablet (768x1024), Mobile (375x812)
- Check: No console errors, no failed requests, UI matches design system
- **If issues found: fix and retest**

### Commit & Deploy
- Commit with clear messages, push to remote
- Deploy via Render (auto on push) or watch deployment logs
- Test deployed app, verify in production

### Completion Checklist
Before marking done:
- [ ] All requirements met
- [ ] All tests passing
- [ ] Visual testing passed (if UI)
- [ ] Documentation updated
- [ ] Deployed and verified

**Don't stop until fully done.**

---

## Style Guide

Follow the Chutes design system: `/home/flori/Dev/chutes/style/chutes_style.md`
- Dark mode with aurora gradients
- Glass morphism cards
- Tomato Grotesk typography
- Moss green (#63D297) accents
