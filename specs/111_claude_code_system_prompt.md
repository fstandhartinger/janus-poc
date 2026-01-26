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
   - **Explicit instructions** on using the Chutes API for media generation (not SVG/ASCII)

2. The bootstrap.sh should copy `agent-pack/prompts/system.md` to `/workspace/CLAUDE.md`

3. **Additional fix needed**: The system prompt must be VERY explicit that:
   - Claude Code has access to REAL image generation APIs
   - It must use `https://image.chutes.ai/generate` - NOT create SVG/PNG files manually
   - Include code example directly in the prompt

## Implementation

### bootstrap.sh changes

Add to bootstrap.sh after creating /workspace:
```bash
# Create CLAUDE.md for Claude Code context
echo "=== Setting up CLAUDE.md for Claude Code ==="
if [ -f /agent-pack/prompts/system.md ]; then
  cp /agent-pack/prompts/system.md /workspace/CLAUDE.md
  echo "CLAUDE.md created from system prompt"
  # Add explicit API instructions
  cat >> /workspace/CLAUDE.md <<'EOF'

## CRITICAL: You Have REAL Media Generation APIs!

**For image generation requests, use the Chutes API (NOT SVG/ASCII art):**

```python
import requests
response = requests.post("https://image.chutes.ai/generate", json={
    "prompt": "your image description here",
    "width": 1024,
    "height": 1024,
    "steps": 30
})
image_base64 = response.json()["b64_json"]
# Return to user as: ![Image](data:image/png;base64,{image_base64})
```

**⚠️ DO NOT create SVG, ASCII art, or placeholder images - USE THE REAL APIs!**
EOF
fi
```

### system.md changes

Added "Media Generation APIs (CRITICAL!)" section with:
- Explicit Python code example for image generation
- Warning NOT to create SVG/ASCII art
- Quick reference for all media APIs

## Progress

1. ✅ CLAUDE.md creation added to bootstrap.sh
2. ✅ First test: Claude Code now attempts to generate image (progress!)
3. ❌ BUT: Created SVG instead of using Chutes API
4. ✅ System prompt updated with explicit API instructions
5. ✅ bootstrap.sh updated with inline API example
6. 🔄 Need to redeploy and test again

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
