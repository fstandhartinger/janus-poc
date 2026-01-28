# Squad Integration Research for Janus

## Executive Summary

Research into the [Squad API repository](https://github.com/chutesai/squad-api) reveals significant reusable components that could accelerate Janus development.

## Key Reusable Components

### High Priority (Direct Adoption)

| Component | What It Does | Effort |
|-----------|--------------|--------|
| **SessionManager** | Thread-safe async HTTP session with connection pooling | Copy as-is |
| **Web Tools** | Playwright browser, screenshot, download, search | Low adaptation |
| **Memory System** | OpenSearch hybrid search, BGE-M3 embeddings, CRUD | Medium |
| **Queue-Based Logging** | Real-time streaming of execution progress | Pattern extraction |

### Medium Priority

| Component | What It Does | Notes |
|-----------|--------------|-------|
| **LLM/VLM Tool Factories** | Dynamic tool creation patterns | Extract pattern |
| **TTS Chunking** | Large text splitting, WAV merging | Useful for audio |
| **X/Twitter Integration** | OAuth, search, posting | Requires paid API |
| **Rate Limiting** | Memcache-based keyed rate limiting | Production-ready |

### Lower Priority

| Component | Notes |
|-----------|-------|
| **DangerZone** | Dynamic tool generation via LLM - Squad-specific |
| **Agent Caller** | Inter-squad communication - needs Janus adaptation |
| **BYOK** | External API proxy - nice-to-have |

## Architecture Patterns Worth Adopting

1. **Dynamic Tool Factories** - Create tools at runtime with custom configs
2. **Hybrid Search** - Combine BM25 + semantic search + date decay
3. **Context Manager Sessions** - Explicit lifecycle, no resource leaks
4. **Modular Storage Backends** - Abstract interface, pluggable implementations

## Technical Compatibility

- **Stack**: Python 3.12 (Squad) vs 3.11 (Janus) - minor version diff
- **Framework**: Both use FastAPI + Uvicorn + SQLAlchemy
- **Async**: Both use asyncio with aiohttp - fully compatible
- **Dependencies**: No conflicts (Playwright, Redis, OpenSearch)

## Recommended Integration Path

### Phase 1: Quick Wins
1. Copy `aiosession.py` SessionManager for connection pooling
2. Extract web tool patterns (already similar to what Janus has)
3. Adopt queue-based logging for Sandy execution streaming

### Phase 2: Memory Enhancement
1. Integrate OpenSearch hybrid search patterns
2. Add BGE-M3 embeddings for semantic memory
3. Implement language detection for multi-lingual support

### Phase 3: Tool Expansion
1. YouTube download tool (ffmpeg integration)
2. Data Universe search (X/Reddit via macrocosmos.ai)
3. Advanced TTS with chunking and voice options

## Key Files to Study

```
squad/
├── aiosession.py          # SessionManager - copy directly
├── util.py                # rate_limit(), rerank() - useful utilities
├── storage/
│   ├── base.py            # OpenSearch + embeddings patterns
│   └── memory.py          # Memory CRUD with hybrid search
├── tool/builtin/
│   ├── web.py             # Playwright, search, download
│   ├── memory.py          # Memory tool interfaces
│   ├── llm.py             # Dynamic LLM tool factory
│   └── transcribe.py      # Whisper integration
└── invocation/
    └── execute.py         # Subprocess + queue logging
```

## Conclusion

Squad provides production-ready infrastructure that aligns well with Janus architecture. The most valuable extractions are:
1. HTTP session management
2. Hybrid search patterns
3. Real-time execution logging
4. Dynamic tool factories

Recommendation: Start with SessionManager and logging patterns, then progressively adopt memory/search infrastructure as Janus scales.
