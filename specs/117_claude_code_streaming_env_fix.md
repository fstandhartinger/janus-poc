# Spec 117: Claude Code Streaming + Env Reliability (Agent-Run)

## Status: COMPLETE

## Context / Why

The Janus baseline agent path (Sandy + Claude Code + model router) is the only
route that can execute tools and produce real media outputs. Two demo prompts
are still failing in the UI:

1. **Image generation**: `generate an image of a cute cat`
2. **Repo analysis**: `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`

Observed failures:
- Claude Code streams progress but never runs media calls (claims missing API key).
- Output is mostly debug noise; the agent finishes without tool usage.
- Streaming feels stalled despite multiple SSE events.
- Image outputs appear as broken data URLs because Claude Code truncates tool results.

This spec hardens the Claude Code execution path without bypassing the model
router or Sandy agent/run API.

## Root Cause Analysis

1. **CHUTES_API_KEY not available inside agent-run**
   - The Sandy agent/run process did not inherit `CHUTES_API_KEY` even though
     the baseline service had it configured.
   - Claude Code reported the variable as unset when asked to print it.
   - Bootstrap ran with the key, but agent-run did not inherit the bootstrap env.

2. **Claude Code flags not controlled in agent/run**
   - The agent-run API owns the CLI invocation, so our baseline service cannot
     pass `--append-system-prompt`, `--include-partial-messages`, or
     `--output-format stream-json` reliably.
   - This can lead to missing partial messages and a lack of prompt guarantees.

3. **Excessive max_tokens from Claude Code**
   - Claude Code requests `max_tokens: 32000` by default.
   - Some Chutes models respond slowly to large max_tokens requests with tools,
     causing “pre-flight check” warnings and long waits before first tokens.
4. **Large tool outputs are truncated**
   - Claude Code writes oversized tool output to `tool-results/*.txt`.
   - The UI sees truncated `data:image` URLs, resulting in broken images.

## Goals

- Claude Code receives **CHUTES_API_KEY** inside the Sandy sandbox.
- Claude Code always appends the **Janus system prompt** (system.md / CLAUDE.md).
- Streaming emits partial message deltas reliably (no “thinking forever”).
- Router requests are bounded to model `max_tokens` to reduce latency.
- Image generation uses the updated Chutes image API contract and saves outputs
  to `/workspace/artifacts` instead of emitting base64.
- Tool-result recovery materializes data URL images into `/workspace/artifacts`.
- The two demo prompts succeed end-to-end in the UI.

## Non-goals

- Replacing Sandy agent/run with a bespoke exec runner.
- Hardcoding special-case logic for the two prompts.

## Solution Design

### A) Enforce Claude Code flags via agent-pack wrapper

Create an agent-pack `bin/claude` wrapper that:
- Preserves provided args but **removes `--verbose`** (noise in JSON stream).
- Ensures `--output-format stream-json` for print mode.
- Adds `--include-partial-messages` for incremental deltas.
- Appends the system prompt content from `JANUS_SYSTEM_PROMPT_PATH`.
- Adds a reasonable `--max-turns` guard (e.g., 8).

Because `/workspace/agent-pack/bin` is first in PATH, Sandy agent/run will use
this wrapper automatically.

### B) Clamp router `max_tokens`

In the agent-pack model router (`agent-pack/router/server.py`):
- Clamp Anthropic `max_tokens` to `model_config.max_tokens` for both streaming
  and non-streaming paths.
- This prevents 32k token requests from slowing tool-heavy calls.

### C) Re-assert CHUTES_API_KEY on Render

Ensure the baseline agent service has `CHUTES_API_KEY` set in Render so the
sandbox environment can inherit it.

### D) Persist env in agent-pack for agent/run

Write a sanitized env export file during bootstrap (no secrets printed to logs)
and have the `claude` wrapper source it when `CHUTES_API_KEY` is missing.
This ensures agent-run processes inherit the sandbox env even if Sandy does not
propagate `env` payloads.

### E) Inject env into Claude Code settings

Extend `~/.claude/settings.json` to include an `env` block with
`CHUTES_API_KEY` and related router variables. Claude Code will load the env
from settings even when Sandy strips environment variables from the process.

### F) Refresh image API docs + prompts

Update the agent-pack docs and system prompts to reflect the current image API:
- `model` field required (use `qwen-image`).
- `num_inference_steps` replaces `steps`.
- Response is raw bytes; write `resp.content` to `/workspace/artifacts/<name>`.
- Example snippet included in CLAUDE.md and system prompt (no base64).

### G) Recover tool-results and materialize artifacts
- Parse `Full output saved to: .../tool-results/*.txt`.
- Read the tool-result file, extract any data URL images, decode to
  `/workspace/artifacts`, and replace data URLs with `/artifacts/<file>` links.

## Implementation Steps

1. Add `baseline-agent-cli/agent-pack/bin/claude` wrapper with the guard flags.
2. Clamp `max_tokens` in the router’s Anthropic handler.
3. Set `CHUTES_API_KEY` for the baseline agent service in Render.
4. Persist env in the agent pack and rehydrate it in the Claude wrapper.
5. Inject env into `~/.claude/settings.json` during bootstrap.
6. Redeploy baseline agent and retest the two demo prompts.
7. Verify image API sample executes successfully with `qwen-image`.

## Acceptance Criteria

- [ ] `CHUTES_API_KEY` prints as non-empty inside Claude Code.
- [ ] Image generation prompt yields a real image via Chutes API.
- [ ] Repo download + explain prompt returns a summary of file contents.
- [ ] Streaming shows real content deltas, not only debug/status noise.
- [ ] Image API examples in docs no longer mention `b64_json` or `steps`.
- [ ] Tool-result recovery prevents broken images from truncated base64.

## Test Plan

1. **Unit:**
   - `pytest baseline-agent-cli/tests/unit/test_sandy_agent_api_streaming.py`

2. **API (gateway):**
   - `POST /v1/chat/completions` with `generate an image of a cute cat`
   - `POST /v1/chat/completions` with repo download + explain prompt

3. **UI (Playwright MCP):**
   - Use Janus chat UI with pre-release password
   - Run the two demo prompts and verify streaming + final output

NR_OF_TRIES: 1
