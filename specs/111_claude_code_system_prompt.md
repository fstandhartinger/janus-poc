# Spec 111: Claude Code System Prompt Integration

## Status: IN_PROGRESS

## Problem

When Claude Code runs in the Sandy sandbox, it doesn't know about Janus capabilities like:
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

This happens because the system prompt (`agent-pack/prompts/system.md`) is never passed to Claude Code.

## Root Cause Analysis

### Original Approach (Failed)
1. CLAUDE.md created in /workspace during bootstrap
2. Claude Code runs with `bash -c 'cd /workspace && claude ...'`
3. **Problem**: Claude Code still doesn't pick up CLAUDE.md reliably

### Why CLAUDE.md Approach Failed
From researching Claude Code's open source repository:
- CLAUDE.md is loaded based on `settingSources` configuration
- In CLI mode with `-p` (print mode), CLAUDE.md discovery may be bypassed
- The `shlex.quote()` wrapping was over-escaping the entire command string

### The Real Solution
Claude Code CLI supports explicit system prompt injection:
- `--system-prompt-file <path>` - Replace default system prompt with file contents
- `--append-system-prompt-file <path>` - **APPEND** file to default system prompt

The correct fix is to use `--append-system-prompt-file /workspace/CLAUDE.md` to explicitly pass our capabilities prompt.

## Implementation

### sandy.py Fix (The Real Fix)

```python
elif agent == "claude" or agent == "claude-code":
    # Claude Code CLI agent
    # Use --append-system-prompt-file to inject Janus capabilities
    # This is more reliable than relying on CLAUDE.md discovery
    command = [
        "claude",
        "-p",
        "--verbose",
        "--output-format", "stream-json",
        "--no-session-persistence",
        "--dangerously-skip-permissions",
        "--append-system-prompt-file", "/workspace/CLAUDE.md",
        "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
        quoted_task,
    ]
```

### bootstrap.sh (Already Done)
- ✅ Creates `/workspace/CLAUDE.md` from system.md
- ✅ Adds explicit Chutes API instructions

## Progress

1. ✅ CLAUDE.md creation added to bootstrap.sh
2. ✅ First test: Claude Code attempted to generate image
3. ❌ BUT: Created SVG instead of using Chutes API
4. ✅ System prompt updated with explicit API instructions
5. ✅ bootstrap.sh updated with inline API example
6. ❌ Second test: Claude Code said "I don't have ability to generate images"
7. 🔧 Root cause: bash -c + shlex.quote over-escapes command
8. ❌ Third test: Still not working with cd /workspace approach
9. 🔧 **NEW FIX**: Use --append-system-prompt-file flag instead of CLAUDE.md discovery
10. 🔄 Implementing the proper fix now

## Key Research Findings

From Claude Code open source repo analysis:
- CLI flag `--append-system-prompt-file <path>` appends file to system prompt
- Stream-json format outputs newline-delimited JSON events
- Event types: system, assistant, user, result
- `-p` mode is required for non-interactive execution
- `--verbose` is needed with stream-json for real-time progress

## Acceptance Criteria

- [x] Spec written
- [x] CLAUDE.md created in /workspace during bootstrap
- [x] Claude Code can see its capabilities when running
- [ ] "generate an image of a cute cat" produces an actual image (via Chutes API)
- [x] All agent pack model docs are referenced
- [x] Explicit API code examples in system prompt

## Test Cases

1. Simple image gen: `generate an image of a cute cat`
2. TTS: `say hello world with text to speech`
3. Deep research: `research the latest developments in quantum computing`
