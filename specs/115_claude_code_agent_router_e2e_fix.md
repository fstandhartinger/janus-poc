# Spec 115: Claude Code Agent Router + System Prompt E2E Reliability

## Status: COMPLETE

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

1. **Claude Code prompt injection broke shell execution**
   - Sandy’s agent runner inlined large system prompt text.
   - CLI launch occasionally hit `unterminated quoted string`, so no output.

2. **System prompt not reliably loaded**
   - CLAUDE.md is only auto-loaded when `cwd` is set correctly.
   - No explicit `--system-prompt-file` / `--append-system-prompt-file` usage.

3. **Model mismatch for Claude Code**
   - Agent-run used MiniMax model IDs for Claude Code, triggering non-Anthropic heuristics.
   - Shortened runtime + inconsistent CLI behavior.

4. **Router visibility + streaming noise**
   - Router only works when bootstrap starts it.
   - Preflight warnings and “working…” lines dominate streaming output.

5. **Claude Code CLI flag conflicts**
   - Installed CLI version rejects `--cwd`.
   - `--append-system-prompt` cannot be combined with `--append-system-prompt-file`.
   - Resulted in immediate CLI errors instead of agent execution.

## Solution Design

### A) Baseline: always prep sandboxes for agent/run
- Upload agent pack for **agent/run** flows.
- Run `agent-pack/bootstrap.sh` to:
  - Create `/workspace/CLAUDE.md`
  - Copy docs into `/workspace/docs/models`
  - Start local router on `127.0.0.1:8000`

### B) Sandy: ensure system prompt is always loaded
- Use `--append-system-prompt-file` for `/workspace/agent-pack/prompts/system.md`.
- Run Claude Code from `/workspace` (prepend `cd /workspace`) so CLAUDE.md memory is picked up.
- Keep minimal non-interactive system prompt to enforce tool usage.
- Fall back to `--append-system-prompt` only when the file is missing.

### C) Router base normalization
- If `apiBaseUrl` is provided:
  - Use `/v1` for OpenAI-compatible agents
  - Use root base for Anthropic clients (Claude Code)

### D) Streaming reliability
- Parse `stream_event` and `result` payloads from Claude Code output.
- Emit content as it arrives in `ChatCompletionChunk.delta.content`.
- Filter known “preflight” warnings from agent output.
- De-duplicate final `result` content when stream deltas already emitted.

## Implementation Steps

1. **baseline-agent-cli**
   - Ensure `execute_via_agent_api` bootstraps router and agent pack.
   - Pick a Claude-compatible model when agent is `claude-code` (router ignores model).
   - Filter noisy preflight output lines in streaming.
   - Provide Anthropic base + key env vars for manual CLI fallback.
   - Update `system.md` with explicit media API instructions.

2. **sandy**
   - Add `--append-system-prompt-file` (system.md) to Claude Code launch.
   - Replace `--cwd` with `cd /workspace` for CLI compatibility.
   - Keep `--verbose` before `--output-format` for stream-json reliability.
   - Avoid `--append-system-prompt` + `--append-system-prompt-file` conflicts.

3. **Tests**
   - Unit test for `stream_event` parsing in baseline.
   - E2E smoke: image generation + repo file explanation.

4. **Docs / History**
   - Update `specs/106` and `specs/111` to COMPLETE when verified.
   - Record milestones in `history.md`.

## Acceptance Criteria

- [x] Claude Code agent-run sees CLAUDE.md and references `/workspace/docs/models`.
- [x] Image generation prompt returns a real image (artifact or inline base64).
- [x] Repo file explanation prompt succeeds with downloaded content.
- [x] Streaming shows incremental content (not just “Thinking…”).
- [x] Streaming does not duplicate final content.
- [x] Router is used via Anthropic Messages API (validated in logs).

## Test Plan

1. **Unit**: `baseline-agent-cli/tests/unit/test_sandy_agent_api_streaming.py`
2. **Integration**: Baseline + Sandy integration tests
3. **E2E API**:
   - `POST /v1/chat/completions` with X-Baseline-Agent: claude-code
4. **UI**: Use Playwright MCP to run both prompts in Janus chat UI.

## Verification (2026-01-27)

- **API image generation**: streamed response contained real JPEG data URL + artifact link (cat image).
- **API file explanation**: streamed download + structured explanation for `api/chute/util.py`.
- **UI**: pre-release gate accepted password; chat UI produced image artifact summary and file explanation.

## Notes

- Claude Code CLI supports `--system-prompt-file` and `--append-system-prompt` in print mode.
- CLAUDE.md must live in `/workspace` for sandbox execution (auto-loaded).

NR_OF_TRIES: 1
