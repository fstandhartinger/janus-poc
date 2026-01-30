# Spec 116: Media Auth + Claude Code Agent Router E2E Fix

## Status: COMPLETE

## Context / Why

The Janus baseline agent path (Sandy + Claude Code + model router) is required for
complex tasks in the chat UI. Two core demo prompts currently fail:

1. **Image generation**: `generate an image of a cute cat`
2. **Repo file analysis**: `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`

Symptoms:
- The agent claims it can’t generate images (falls back to text-only disclaimers)
- The agent appears to “think forever” without streaming useful content

These failures block the primary demo narrative and indicate missing, systemic
configuration rather than model behavior.

## Root Cause Analysis

1. **Missing Chutes API Authorization in prompts/docs**
   - The agent pack’s `text-to-image.md` and system prompts showed image
     generation examples **without** the required `Authorization: Bearer $CHUTES_API_KEY` header.
   - Claude Code followed the prompt examples and made unauthenticated requests,
     leading to 401 errors from `https://image.chutes.ai/generate`.
   - Result: the model interpreted the failure as “image generation not available.”

2. **Agent prompt duplication inconsistencies**
   - Image generation instructions appear in multiple places:
     - `agent-pack/prompts/system.md` (CLAUDE.md source)
     - `agent-pack/bootstrap.sh` inline CLAUDE.md augmentation
     - `janus_baseline_agent_cli/prompts/system.md`
     - `janus_baseline_agent_cli/services/sandy.py` inline instructions
   - Only some of these had auth headers, so behavior depended on which prompt
     path was active.

3. **Streaming + tool use already fixed, but masked by auth failure**
   - After router tool compatibility fixes, Claude Code can invoke tools and
     stream responses, but the missing Authorization still prevented media output
     (so UI looked stalled or “thinking”).

4. **CHUTES_API_KEY missing inside Sandy agent/run**
   - Claude Code reports `CHUTES_API_KEY` unset in the sandbox.
   - This blocks media calls even when prompts are correct.
5. **Large media outputs truncated**
   - Claude Code can emit `Output too large... tool-results/*.txt`, causing truncated
     data URLs to reach the UI and render as broken images.

## Goals

- Image generation prompts include **Authorization headers** everywhere they can
  be referenced by Claude Code.
- Claude Code clearly knows to use `CHUTES_API_KEY` for media endpoints.
- The two demo prompts succeed end-to-end in the UI.
- Streaming shows meaningful content while the agent works.
- Image outputs are delivered as artifacts (not truncated base64).

## Non-goals

- One-off hacks to force specific outputs
- Replacing the router or bypassing Claude Code

## Solution Design

### A) Normalize Authorization across all prompts

- Update `agent-pack/models/text-to-image.md` to include
  `Authorization: Bearer $CHUTES_API_KEY`.
- Update `agent-pack/prompts/system.md` to include a full example with
  `Authorization` header.
- Update `agent-pack/bootstrap.sh` CLAUDE.md snippet and
  `JANUS_SYSTEM_PROMPT` fallback to include auth.
- Update `janus_baseline_agent_cli/prompts/system.md` and
  `janus_baseline_agent_cli/services/sandy.py` inline instructions to include
  auth headers and `CHUTES_API_KEY` usage.

### B) Ensure agent-run helper examples include Authorization

- Update `agent-pack/run_agent.py` example snippets to include the
  `Authorization` header across media and LLM requests.

### C) Pass CHUTES_API_KEY into Sandy agent/run

- Include `env` in the `agent/run` payload so Claude Code inherits
  `CHUTES_API_KEY` and related sandbox variables for media calls.

### D) Ensure CHUTES_API_KEY is set on Render baseline agent

- Set `CHUTES_API_KEY` on the baseline agent Render service so the sandbox env
  can be populated during agent/run.

### E) Prefer artifacts over data URLs
- Update prompts/examples to save images under `/workspace/artifacts`.
- When tool output is too large, recover `tool-results/*.txt` and materialize
  any data URL images into `/workspace/artifacts` before returning artifacts.

## Acceptance Criteria

- [ ] Claude Code uses authenticated Chutes API calls for image generation
- [ ] `generate an image of a cute cat` returns a real image in chat UI
- [ ] `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`
      succeeds with a summary of file contents
- [ ] Streaming shows incremental content in the UI (not only “Thinking...”) 

## Test Plan

1. **Unit/Integration**
   - Run `./scripts/run-tests.sh`

2. **UI E2E (Playwright MCP)**
   - Prompt: `generate an image of a cute cat`
   - Prompt: `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`
   - Validate streamed content and final response

## Notes

- This spec only addresses auth/prompt correctness.
- Router tool compatibility and streaming parsing are covered by Spec 115.

---

NR_OF_TRIES: 0
