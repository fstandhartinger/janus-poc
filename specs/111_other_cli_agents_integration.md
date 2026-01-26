# Spec 111: Other CLI Agents Integration

## Status: RESEARCH COMPLETE - IMPLEMENTATION DEFERRED

## Context / Background

Sandy supports multiple CLI agent backends beyond Claude Code. Testing revealed that most agents don't produce command output through Sandy's streaming, limiting their usefulness for shell execution tasks. This spec documents the findings and outlines potential fixes.

## Agent Testing Results (2026-01-26)

| Agent | Response Time | Shell Execution | Output Captured | Status |
|-------|--------------|-----------------|-----------------|--------|
| Claude Code | 6.3s | YES | YES | **WORKING** |
| Codex | 15.2s | NO | "Agent completed without output" | Needs investigation |
| OpenCode | 6.5s | NO | Only plugin installation msgs | TUI mode issue |
| OpenHands | 12.8s | NO | "terminal completed" | Docker isolation |
| Droid | 2.7s | NO | "Agent completed without output" | Minimal config |
| Aider | 6-8s | NO | Code suggestions only | By design (editor) |

## Agent Analysis

### Codex (OpenAI)

**Project**: https://github.com/openai/codex

**What It Is**: OpenAI's coding assistant CLI, similar to Claude Code but for OpenAI models.

**Current Issue**: Agent completes but no output is captured by Sandy.

**Potential Fix**:
- Codex may be writing to a file or stdout in a way Sandy doesn't capture
- Need to investigate Sandy's `agent-output` event streaming for Codex
- May require `--output-format json` or similar flag

**Bootstrap Configuration**:
```bash
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="${CHUTES_API_KEY}"
```

### OpenCode

**Project**: https://github.com/anomalyco/opencode

**What It Is**: Go-based TUI coding assistant that wraps LLM APIs.

**Current Issue**: Runs in TUI mode, outputs only plugin installation messages.

**Potential Fix**:
- Use non-interactive mode: `opencode run "prompt"` instead of `opencode "prompt"`
- Add `--format json` for structured output
- May need `--no-tui` flag if available

**Correct CLI Usage**:
```bash
# Wrong (TUI mode)
opencode "task prompt"

# Correct (non-interactive)
opencode run "task prompt" --format json
```

**Bootstrap Configuration**:
```bash
export OPENCODE_API_URL="http://127.0.0.1:8000/v1"
export OPENCODE_API_KEY="${CHUTES_API_KEY}"
```

### OpenHands

**Project**: https://github.com/All-Hands-AI/OpenHands

**What It Is**: Python-based autonomous coding agent with browser and terminal capabilities.

**Current Issue**: Runs in Docker isolation, outputs "terminal completed" without actual content.

**Potential Fix**:
- OpenHands has its own async architecture and Docker sandboxing
- May conflict with Sandy's sandboxing approach
- Need to run OpenHands in "headless" or "API" mode
- Output may be written to workspace files rather than stdout

**Architecture Consideration**:
OpenHands already provides its own sandboxing via Docker. Running it inside Sandy's sandbox creates nested isolation that may break output streaming.

**Alternative**: Run OpenHands as a standalone service and integrate via API rather than CLI.

### Droid

**Project**: Likely a minimal Sandy-specific agent

**Current Issue**: Fastest response (2.7s) but no output.

**Potential Fix**:
- May require specific Sandy configuration
- Possibly a placeholder or stub agent
- Need Sandy documentation to understand expected behavior

### Aider

**Project**: https://github.com/paul-gauthier/aider

**What It Is**: AI pair programming tool that edits files directly.

**Current Issue**: By design, Aider is a code EDITOR, not a command EXECUTOR.

**Behavior**:
- When asked to "search the web", Aider writes code that would search
- When asked to "run a command", Aider suggests code changes
- No shell execution capability - intentional design choice

**Use Cases**:
- Code refactoring
- Bug fixes in existing files
- Adding new features to codebase
- NOT suitable for: web searches, file downloads, command execution

**Configuration** (already working):
```bash
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="${CHUTES_API_KEY}"
```

## Recommendations

### Priority 1: Keep Claude Code as Default
Claude Code is the only agent that reliably:
- Executes shell commands
- Captures and streams output
- Works with the Anthropic API format

### Priority 2: Fix OpenCode
OpenCode has the most potential as an alternative:
- Fast (6.5s response)
- Go-based (lightweight)
- Has non-interactive mode

**Action Items**:
1. Update Sandy's OpenCode command to use `opencode run "prompt"`
2. Add `--format json` flag for structured output
3. Test output capture

### Priority 3: Investigate Codex
Codex should work similarly to Claude Code:
- Both are terminal-based agents
- Both use similar prompting patterns

**Action Items**:
1. Check if Codex has output format options
2. Review Sandy's stdout/stderr capture for Codex process
3. Test with explicit `--json` or similar flag

### Priority 4: Defer OpenHands
OpenHands' architecture conflicts with Sandy's approach:
- Double Docker sandboxing
- Async event-driven output
- Complex setup

**Recommendation**: Consider OpenHands as a standalone baseline option rather than Sandy agent.

### Priority 5: Accept Aider Limitations
Aider is valuable for code editing but not for command execution:
- Keep as option for code-focused tasks
- Document that it won't execute commands
- Use `X-Baseline-Agent: aider` header for editing tasks

## Implementation Plan

### Phase 1: Documentation (DONE)
- Document agent capabilities in spec 109
- Create this spec with research findings

### Phase 2: OpenCode Fix
```python
# In sandy.py, update OpenCode command:
elif agent == "opencode":
    command = [
        "opencode",
        "run",  # Non-interactive mode
        quoted_task,
        "--format", "json",  # Structured output
    ]
```

### Phase 3: Codex Investigation
1. Add debug logging to Sandy for Codex stdout/stderr
2. Test different output format options
3. Check if output goes to file vs stdout

### Phase 4: Agent Selection UI
Add agent selection to chat UI with capability badges:
- Claude Code: Shell, Web, Downloads, Code
- Aider: Code only
- OpenCode: TBD
- Codex: TBD

## Related Files

- `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` - Agent command building
- `baseline-agent-cli/agent-pack/bootstrap.sh` - Agent environment setup
- `specs/109_agentic_chat_response_e2e.md` - Original testing spec

## References

- OpenCode CLI: https://opencode.ai/docs/cli/
- OpenCode GitHub: https://github.com/anomalyco/opencode
- OpenHands: https://github.com/All-Hands-AI/OpenHands
- Aider: https://github.com/paul-gauthier/aider
- Codex: https://github.com/openai/codex

NR_OF_TRIES: 0
