# Spec 110: Claude Code Streaming Fix

## Status: COMPLETE

## Summary

Fix Claude Code CLI integration to properly stream real-time events and remove pattern-based complexity detection in favor of LLM-only routing.

## Changes Made

### 1. Claude Code CLI Command Flags (sandy.py)

**Before:**
```python
command = [
    "claude",
    "-p",
    "--output-format", "stream-json",
    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
    quoted_task,
]
```

**After:**
```python
command = [
    "claude",
    "-p",  # Print mode (non-interactive)
    "--verbose",  # Required for stream-json progress events
    "--output-format", "stream-json",
    "--no-session-persistence",  # Fresh context each run
    "--dangerously-skip-permissions",  # YOLO mode
    "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch",
    quoted_task,
]
```

Key additions:
- `--verbose`: REQUIRED for stream-json to emit real-time events (tool use, progress, etc.)
- `--no-session-persistence`: Ensures fresh context each run without session contamination
- `--dangerously-skip-permissions`: YOLO mode for automated sandbox execution

### 2. Complexity Detection Changes (complexity.py)

- **Removed**: `SIMPLE_CONVERSATION_PATTERNS` regex-based detection
- **Kept**: `TRIVIAL_GREETINGS` set for instant fast-path (hi, hello, thanks, etc.)
- All other messages now go through the LLM verifier for smart routing decisions

### 3. LLM Routing Model Update

Changed the default routing model from `XiaomiMiMo/MiMo-V2-Flash` to `tngtech/TNG-R1T-Chimera-Turbo`:
- Faster response times
- Better at understanding intent
- More reliable routing decisions

Files updated:
- `config.py`: `llm_routing_model` default
- `complexity.py`: `ROUTING_MODELS` list

## Acceptance Criteria

- [x] Claude Code streams real-time progress events (tool use, thinking, text)
- [x] No more "(no content)" messages during long-running agent tasks
- [x] Pattern-based detection removed, LLM verifier used for all non-trivial messages
- [x] TNG-R1T-Chimera-Turbo used as primary routing model
- [x] All existing tests pass

## Test Cases

Test prompt for agent:
```
download https://github.com/chutesai/chutes-api/blob/main/api/chute/util.py and explain it to me
```

Expected behavior:
1. LLM router correctly identifies this as complex (needs agent)
2. Claude Code starts in sandbox
3. Real-time streaming shows tool use (Bash, WebFetch, etc.)
4. User sees progress updates in chat
5. Final response includes code analysis

## References

- Claude Code CLI Reference: https://code.claude.com/docs/en/cli-reference
- ralph-loop.sh script uses the same flags successfully
