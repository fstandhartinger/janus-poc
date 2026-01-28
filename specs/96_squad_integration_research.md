# Spec 96: Squad Tool Integration Research

## Status: COMPLETE

## Context / Why

Jon mentioned that Squad has many reusable tools (web search, youtube download, ffmpeg, headless browser, memory, streaming, etc.) that could accelerate Janus development. Before building new components, we should research what Squad offers and determine what can be reused.

## Goals

- Research Squad repository architecture and available tools
- Document which components are reusable in Janus
- Create integration recommendations
- Produce a technical summary document

## Research Results

Research completed. See [docs/squad-integration-research.md](../docs/squad-integration-research.md) for full findings.

### Key Findings

**High Reusability:**
1. **SessionManager** (aiosession.py) - Thread-safe async HTTP session pooling - copy as-is
2. **Web Tools** - Playwright browser, screenshots, downloads - similar to existing Janus
3. **Memory System** - OpenSearch hybrid search with BGE-M3 embeddings
4. **Queue-Based Logging** - Real-time execution progress streaming

**Medium Reusability:**
1. LLM/VLM tool factory patterns
2. TTS chunking and WAV merging
3. Rate limiting utilities
4. X/Twitter integration (requires paid API)

**Lower Reusability:**
1. DangerZone (dynamic tool generation) - too Squad-specific
2. Agent Caller - needs adaptation for Janus architecture

### Compatibility

- Both use FastAPI + Uvicorn + SQLAlchemy
- Both use asyncio - fully compatible
- Python version difference (3.12 vs 3.11) is minor

### Recommended Integration Path

1. **Quick Wins**: SessionManager, logging patterns
2. **Memory**: OpenSearch hybrid search, embeddings
3. **Tools**: YouTube download, Data Universe search

## Deliverables

- [x] Research Squad repository
- [x] Create summary document at `docs/squad-integration-research.md`
- [x] Send Telegram notification with summary

## Files Created

```
docs/squad-integration-research.md  # Technical research summary
```

## Related Specs

- Spec 72: Memory Service Backend
- Spec 73: Memory Integration Baselines

NR_OF_TRIES: 1
