# Spec 111: Claude Code System Prompt Integration

## Status: COMPLETE

## Problem

When Claude Code runs in the Sandy sandbox, it does not reliably know about Janus
capabilities like:
- Image generation via Chutes APIs
- Text-to-speech, video generation
- Deep research capabilities
- Browser automation
- Sandbox management

Example failure:
```
User: "generate an image of a cute cat"
Claude Code: "I can't generate images directly - I'm a text-based AI assistant..."
```

This happens because the system prompt (`agent-pack/prompts/system.md`) and docs are
not consistently loaded in the Sandy agent-run flow, or are not appended to the
Claude Code CLI invocation.

## Root Cause Analysis

1. **Agent pack not loaded for agent/run**
   - `execute_via_agent_api()` did not upload the agent pack or run bootstrap.
   - Result: `/workspace/CLAUDE.md` never exists and the prompt/model docs are missing.

2. **Sandy agent-run bypasses CLAUDE.md**
   - Sandy’s `AgentRunner` controls the CLI invocation, so CLAUDE.md is not guaranteed
     to be appended to the prompt on every run.
   - Without `--append-system-prompt` or `systemPromptPath`, Claude Code misses Janus capabilities.

3. **Router base URL mismatch**
   - Claude Code expects an Anthropic Messages API base URL.
   - When the router URL is wrong (e.g. `/v1` appended twice), the agent hangs waiting for a model response.

## Research Findings

From Claude Code docs:
- `--system-prompt-file` and `--append-system-prompt` are supported in print mode.
- `CLAUDE.md` memory files are automatically loaded from the working directory tree.

**Key insight:** `CLAUDE.md` is the supported, auto-loaded mechanism for persistent
instructions, but the robust fix is to also **append** the system prompt explicitly
via CLI flags so agent/run runs are deterministic.

## Solution

### 1) Baseline: always prep the sandbox before agent/run
- Upload the agent pack for `execute_via_agent_api()` and `complete_via_agent_api()`.
- Run `agent-pack/bootstrap.sh` to:
  - Create `/workspace/CLAUDE.md` from `system.md`
  - Copy docs into `/workspace/docs/models`

### 2) Sandy agent-run: append the system prompt deterministically
- Ensure `/workspace/CLAUDE.md` exists (from bootstrap).
- Always pass `systemPromptPath=/workspace/agent-pack/prompts/system.md` to Sandy agent/run
  so the CLI appends it even if CLAUDE.md is not loaded.

### 2b) Enforce Claude Code prompt flags via wrapper
- Add an agent-pack `bin/claude` wrapper so Sandy agent/run always:
  - uses `--output-format stream-json` + `--include-partial-messages`
  - appends the system prompt from `JANUS_SYSTEM_PROMPT_PATH`
  - avoids noisy `--verbose` logs that break JSON parsing

### 3) Router base normalization
- When `apiBaseUrl` is provided to Sandy agent-run:
  - Use `/v1` for OpenAI-compatible clients
  - Use root base for Anthropic (`/v1/messages` is appended by Claude Code)

### 4) Streaming content reliability
- Handle Claude Code `stream_event` and `result` payloads so content streams to UI.

## Acceptance Criteria

- [ ] Claude Code sees Janus capabilities (from CLAUDE.md) in Sandy agent-run
- [ ] `generate an image of a cute cat` produces a real image via Chutes API
- [ ] `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it` succeeds
- [ ] Claude Code uses the Anthropic Messages router (not a single fixed model)
- [ ] Streaming shows actual response content (not just “Thinking...”)

## Test Cases

1. **Image generation**
   - Prompt: `generate an image of a cute cat`
   - Expect: PNG artifact or inline base64 image

2. **Repo file analysis**
   - Prompt: `download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it`
   - Expect: file downloaded + explanation

3. **Streaming smoke**
   - Confirm `stream_event` deltas appear in UI while agent is working

NR_OF_TRIES: 1
