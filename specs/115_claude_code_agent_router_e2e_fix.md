# Spec 115: Claude Code Agent Router + System Prompt E2E Reliability

## Status: IN_PROGRESS

## Context / Why

The Janus chat UI relies on the baseline agent path (Sandy + Claude Code) for
complex, tool-using tasks. Two core demo prompts currently fail:

1. **Image generation**: `generate an image of a cute cat`
2. **Repo file analysis**: `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`

Failures show either:
- Claude Code claiming it can’t generate images, or
- Endless “thinking” without streaming real content.

This spec ensures the agent path is deterministic, uses the model router, and
streams useful output in the UI.

## Goals

- Claude Code uses **the Janus model router** (Anthropic Messages API) for all
  model calls, including fallbacks.
- The **agent pack** is present inside Sandy sandboxes, including system prompt
  docs (`/workspace/CLAUDE.md`, `/workspace/docs/models/*`).
- The system prompt is **guaranteed** to be read by Claude Code in print mode.
- Streaming output shows **real content** as it is produced (not just “Thinking”).
- The two core demo prompts succeed end-to-end in the chat UI.

## Non-goals

- One-off hacks to force the two prompts to pass.
- Replacing Sandy agent/run with a bespoke streaming runner.
- Changing the Janus router logic beyond required compatibility fixes.

## Root Cause Summary

1. **Agent pack not loaded for agent/run**
   - `execute_via_agent_api()` skipped upload + bootstrap.
   - No `/workspace/CLAUDE.md`, docs, or local router.

2. **Claude Code system prompt ignored**
   - Sandy’s AgentRunner appended internal prompts only.
   - CLAUDE.md never loaded or appended.

3. **Router base mismatch**
   - Claude Code uses Anthropic base URLs; OpenAI tools expect `/v1`.
   - Missing router causes long hangs or empty output.

4. **Streaming output gaps**
   - `stream_event` and `result` payloads from Claude Code weren’t parsed.
   - UI sees “thinking” but no answer.

## Solution Design

### A) Baseline: always prep sandboxes for agent/run
- Upload agent pack for **agent/run** flows.
- Run `agent-pack/bootstrap.sh` to:
  - Create `/workspace/CLAUDE.md`
  - Copy docs into `/workspace/docs/models`
  - Start local router on `127.0.0.1:8000`

### B) Sandy: ensure CLAUDE.md is auto-loaded
- Ensure `/workspace/CLAUDE.md` exists (from bootstrap).
- Claude Code runs from `/workspace`, so it auto-loads `CLAUDE.md`.
- Keep minimal non-interactive system prompt to enforce tool usage.

### C) Router base normalization
- If `apiBaseUrl` is provided:
  - Use `/v1` for OpenAI-compatible agents
  - Use root base for Anthropic clients (Claude Code)

### D) Streaming reliability
- Parse `stream_event` and `result` payloads from Claude Code output.
- Emit content as it arrives in `ChatCompletionChunk.delta.content`.

## Implementation Steps

1. **baseline-agent-cli**
   - Upload agent pack + run bootstrap in `execute_via_agent_api` and `complete_via_agent_api`.
   - Default `apiBaseUrl` to local router when `use_model_router` is enabled.
   - Add `stream_event` + `result` parsing for agent-run streaming.

2. **sandy**
   - Normalize router base URLs for OpenAI vs Anthropic.
   - Append `/workspace/CLAUDE.md` to Claude Code command if present.

3. **Tests**
   - Unit test for `stream_event` parsing in baseline.
   - E2E smoke: image generation + repo file explanation.

4. **Docs / History**
   - Update `specs/106` and `specs/111` to COMPLETE when verified.
   - Record milestones in `history.md`.

## Acceptance Criteria

- [ ] Claude Code agent-run sees CLAUDE.md and references `/workspace/docs/models`.
- [ ] Image generation prompt returns a real image (artifact or inline base64).
- [ ] Repo file explanation prompt succeeds with downloaded content.
- [ ] Streaming shows incremental content (not just “Thinking…”).
- [ ] Router is used via Anthropic Messages API (validated in logs).

## Test Plan

1. **Unit**: `baseline-agent-cli/tests/unit/test_sandy_agent_api_streaming.py`
2. **Integration**: Baseline + Sandy integration tests
3. **E2E API**:
   - `POST /v1/chat/completions` with X-Baseline-Agent: claude-code
4. **UI**: Use Playwright MCP to run both prompts in Janus chat UI.

## Notes

- Claude Code CLI supports `--system-prompt-file` and `--append-system-prompt` in print mode.
- CLAUDE.md must live in `/workspace` for sandbox execution (auto-loaded).

NR_OF_TRIES: 0
