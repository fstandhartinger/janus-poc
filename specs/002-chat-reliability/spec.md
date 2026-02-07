# Specification: Chat Reliability Contract

## Feature: Fast Path vs Agent Sandbox (Baseline CLI Agent)

### Overview
Janus PoC chat must feel instant for simple questions, while reliably switching into
agentic execution (via Sandy sandboxes) for complex tasks. The UI must continuously
stream understandable progress updates in the Thinking panel until final answer content
arrives, and it must render/download multimodal outputs (images, audio, video, files)
cleanly. Generative UI fragments must render safely and predictably.

### Test-First Validation (Do Before Implementing Anything)
1. Run the existing automated suites (unit + integration + smoke) and note failures.
2. In the chat UI, run through the full examples surface:
   - Demo prompts: `ui/src/data/demoPrompts.ts`
   - Plus menu tags: generate image/video/audio, deep research, web search
3. For each scenario below, confirm the observed behavior matches the acceptance criteria.
4. Only implement changes if any criterion fails.

### User Stories
- As a user, I want simple questions to return very quickly so that chat feels snappy.
- As a user, I want complex tasks to transparently run in a sandboxed agent so that tools
  (git clone, file creation, browser automation) work reliably and safely.
- As a user, I want to see continuous progress updates so that long tasks never feel stuck.
- As a user, I want generated media and files to be previewable and downloadable so that
  I can consume outputs without manual work.
- As a user, I want interactive UI widgets to render safely so that I can use generated
  calculators/forms without trusting arbitrary page access.

---

## Functional Requirements

### FR-1: Fast Path Routing (No Agent Sandbox)
Simple questions that do not require up-to-date web research or tool execution must use
the fast path and avoid Sandy.

**Acceptance Criteria:**
- [ ] For a prompt like "Explain why the sky is blue", the response completes quickly and
  does not create a Sandy sandbox.
- [ ] The response contains a direct answer with minimal/no "agent progress" status spam.
- [ ] Any optional reasoning_content shown for fast path is short and non-disruptive.

### FR-2: Agentic Routing (Sandy Sandbox)
Complex tasks that require tool usage must reliably route to the Sandy-backed agent path.

**Acceptance Criteria:**
- [ ] For agentic demo prompts (clone/analyze/download), a Sandy sandbox is created and used.
- [ ] The response includes a helpful final answer plus any produced artifacts (files).
- [ ] Sandbox lifecycle events are surfaced to the user via `reasoning_content` updates.

### FR-3: Model Router Works in Both Modes
The "janus-router" model must behave consistently:
- Fast path uses router decisions without introducing significant latency.
- Agent mode (Claude Code or other CLI agent inside Sandy) can call the router API correctly.

**Acceptance Criteria:**
- [ ] Fast path requests using model "janus-router" produce valid answers and include
  response metadata indicating the resolved upstream model (where available).
- [ ] Sandy `/agent/run` requests configured to use "janus-router" provide a valid API base URL
  and do not error due to missing router configuration.
- [ ] A regression test/verification exists for the previously observed Claude Code flag conflict
  (`--append-system-prompt` vs `--append-system-prompt-file`) and it does not recur.

### FR-4: Streaming UX Contract (Thinking + Final Answer)
The frontend must present a constant stream of understandable updates in the Thinking panel
until actual answer content arrives.

**Acceptance Criteria:**
- [ ] During agentic runs, the Thinking panel is visible and streams updates continuously.
- [ ] The Thinking panel stays expanded while the agent is working and auto-collapses only after
  streaming finishes and the final answer content exists.
- [ ] Streaming never appears "stuck": either progress updates arrive or a clear timeout/error is shown.

### FR-5: Multimodal Outputs Render Nicely
Images, audio, and video should render inline where appropriate, and always be downloadable.

**Acceptance Criteria:**
- [ ] Image outputs render as images (message content and/or artifacts).
- [ ] Audio outputs render with an audio player and provide a download action.
- [ ] Video outputs render with an inline video player and provide a download action.
- [ ] Non-media file artifacts render as attachment cards and are downloadable.

### FR-6: Files Produced by the Agent Are Downloadable
If the agent produces files (reports, code, datasets), the user can reliably download them.

**Acceptance Criteria:**
- [ ] Artifacts served via the UI `/api/artifacts/...` route support large file delivery
  without loading entire files into memory.
- [ ] Video/audio playback works for cached artifacts (including partial requests where applicable).
- [ ] Download links have stable filenames and do not require manual URL manipulation.

### FR-7: Generative UI Fragments Render Safely
Generated interactive HTML blocks should render in an isolated container with predictable sizing.

**Acceptance Criteria:**
- [ ] `html-gen-ui` code fences render in a sandboxed iframe (scripts allowed, no same-origin).
- [ ] The iframe resizes to fit content without overflowing the chat layout.
- [ ] The agent pack/system prompt includes guidance for emitting `html-gen-ui` blocks.

---

## Success Criteria
- Fast path answers feel immediate for simple questions.
- Agentic tasks are robust and do not randomly fail due to sandbox/router configuration.
- Progress feedback is continuous and human-readable.
- Media and file outputs are easy to consume (preview + download).

---

## Dependencies
- Sandy sandbox service (`../sandy`) with `/api/sandboxes/*` endpoints and `/agent/run`.
- Baseline CLI agent (`baseline-agent-cli`) complexity routing and Sandy integration.
- Janus UI artifact caching and serving (`ui/src/app/api/artifacts/*`).

## Assumptions
- Environment variables required for Sandy and routing are configured in local dev and Render.
- Demo prompts and plus-menu tags are representative of the desired product behavior.

---

## Completion Signal

### Implementation Checklist
- [ ] Verify all acceptance criteria via automated tests and targeted manual checks.
- [ ] Add/adjust unit tests for UI rendering of artifacts (audio/video/files) and Thinking behavior.
- [ ] Ensure artifact serving supports efficient delivery for large media files.
- [ ] Confirm baseline agent prompt includes instructions for artifacts and `html-gen-ui`.
- [ ] Document any new env var requirements in the appropriate docs.

### Testing Requirements

The agent MUST complete ALL before outputting the magic phrase:

#### Code Quality
- [ ] All existing unit tests pass
- [ ] All existing integration tests pass
- [ ] New tests added for new functionality
- [ ] No lint/typecheck errors

#### Functional Verification
- [ ] All acceptance criteria verified
- [ ] Edge cases handled (empty outputs, artifact-only responses, large media artifacts)
- [ ] Error handling in place (timeouts, missing Sandy/router config)

#### Visual Verification (UI)
- [ ] Desktop view looks correct (Thinking stream, media rendering)
- [ ] Mobile view looks correct (no overflow, media sizing)

#### Console/Network Check (Web)
- [ ] No JavaScript console errors
- [ ] No failed network requests during demo prompt runs

### Iteration Instructions
If ANY check fails:
1. Identify the specific issue
2. Fix the code
3. Run tests again
4. Verify all criteria
5. Commit and push
6. Check again

**Only when ALL checks pass, output:** `<promise>DONE</promise>`

