---
name: speckit-implement
description: Execute implementation using Ralph Wiggum iterative loops on specs
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Overview

This skill launches the Ralph Wiggum implementation loop to process specifications autonomously. The agent iterates until acceptance criteria and Completion Signal requirements pass.

## Prerequisites

1. **At least one spec**: Specs must exist in `specs/` with Completion Signal sections

2. **Context files**:
   - `.specify/memory/constitution.md` — Project principles
   - `AGENTS.md` — Development guidelines
   - `RALPH_PROMPT.md` — Master prompt (optional, can use inline)

## Execution

### Option A: Single Spec

If `$ARGUMENTS` specifies a single spec (e.g., "001-user-auth"):

1. Read the spec from `specs/$ARGUMENTS/spec.md`
2. Read `.specify/memory/constitution.md` for project principles
3. Read `AGENTS.md` for development guidelines
4. Implement all requirements
5. Complete ALL items in the Completion Signal section
6. Run all tests (unit, integration, browser, visual)
7. Verify no console/network errors
8. Commit and push changes
9. Deploy if required and verify
10. Iterate until all checks pass
11. Output `<promise>DONE</promise>` when ALL checks pass

### Option B: All Specs (Master Loop)

If no specific spec provided, run the master loop:

1. Read `.specify/memory/constitution.md` for project principles
2. Read `AGENTS.md` for development guidelines
3. Work through all specifications in `specs/` folder in numerical order
4. For each spec:
   - Read the spec from `specs/{spec-name}/spec.md`
   - Implement all requirements
   - Complete ALL items in the Completion Signal section
   - Commit, push, and verify deployment
   - Update history if required
   - Move to next spec
5. Output `<promise>ALL_DONE</promise>` when all specs complete

## Alternative: Shell Script

You can also run the Ralph loop via shell:

```bash
./scripts/ralph-loop-codex.sh
```

Or for a specific spec:

```bash
./scripts/ralph-loop-codex.sh 001-user-auth
```
