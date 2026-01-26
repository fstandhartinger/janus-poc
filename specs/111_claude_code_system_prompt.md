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

## Root Cause

In `sandy.py`, the Claude Code command is:
```python
command = [
    "claude",
    "-p",
    "--verbose",
    "--output-format", "stream-json",
    "--no-session-persistence",
    "--dangerously-skip-permissions",
    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
    quoted_task,  # Just the user message!
]
```

Compare with Aider which properly includes the system prompt:
```python
command = [
    "aider",
    "--read", system_prompt_path,  # System prompt passed!
    "--message", quoted_task,
]
```

## Solution

Claude Code reads `CLAUDE.md` automatically from the working directory. The fix:

1. **Create `/workspace/CLAUDE.md`** during bootstrap that contains:
   - Full system prompt with Janus capabilities
   - Links to model documentation files
   - Instructions on how to generate media

2. The bootstrap.sh should copy `agent-pack/prompts/system.md` to `/workspace/CLAUDE.md`

## Implementation

### bootstrap.sh changes

Add to bootstrap.sh after creating /workspace:
```bash
# Create CLAUDE.md for Claude Code context
echo "=== Setting up CLAUDE.md for Claude Code ==="
if [ -f /agent-pack/prompts/system.md ]; then
  cp /agent-pack/prompts/system.md /workspace/CLAUDE.md
  echo "CLAUDE.md created from system prompt"
fi
```

## Acceptance Criteria

- [x] Spec written
- [ ] CLAUDE.md created in /workspace during bootstrap
- [ ] Claude Code can see its capabilities when running
- [ ] "generate an image of a cute cat" produces an actual image
- [ ] All agent pack model docs are referenced

## Test Cases

1. Simple image gen: `generate an image of a cute cat`
2. TTS: `say hello world with text to speech`
3. Deep research: `research the latest developments in quantum computing`
