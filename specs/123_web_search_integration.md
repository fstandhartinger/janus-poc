# Spec 123: Web Search Integration for Agents

## Status: COMPLETE

**Priority:** High
**Complexity:** Medium
**Prerequisites:** None

---

## Problem Statement

When users ask agents to perform web searches (e.g., "Search the web for the latest AI developments in 2026"), the search fails with empty results. The agent reports "web search results did not return any actual content" and cannot fulfill the request.

**User Impact:** Web search is a core capability expected from AI agents. Without it, research tasks fail completely.

---

## Root Cause Analysis

Based on research of the codebase:

1. **Claude Code (Baseline CLI)** relies on Claude's native `WebSearch` tool, but this requires proper API configuration
2. **Baseline LangChain** has web search implemented via Tavily or chutes-search fallback, but may lack API keys
3. **chutes-search** (sibling project) implements web search with Serper API + SearXNG fallback

The issue is that web search API keys are not configured in the deployed environment.

---

## Solution

Integrate Serper API for web search across all agent paths, following the pattern used in `../chutes-search`.

### Implementation Steps

### 1. Add Serper API Configuration

**File: `gateway/janus_gateway/config.py`**
```python
# Web Search Configuration
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
SEARXNG_API_URL: str = os.getenv("SEARXNG_API_URL", "")
```

### 2. Create Web Search Service

**File: `gateway/janus_gateway/services/web_search.py`**
```python
import httpx
from typing import List, Dict, Any, Optional

async def serper_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """Execute web search via Serper API."""
    api_key = config.SERPER_API_KEY
    if not api_key:
        raise ValueError("SERPER_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("link", ""),
            "snippet": r.get("snippet", ""),
        }
        for r in data.get("organic", [])
    ]
```

### 3. Add Web Search Endpoint

**File: `gateway/janus_gateway/routers/search.py`**
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["search"])

class SearchRequest(BaseModel):
    query: str
    num_results: int = 10

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

@router.post("/web", response_model=List[SearchResult])
async def web_search(request: SearchRequest):
    """Perform web search using Serper API."""
    try:
        results = await serper_search(request.query, request.num_results)
        return results
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### 4. Configure Baseline LangChain

Ensure environment variables are set:
```bash
BASELINE_LANGCHAIN_TAVILY_API_KEY=<key>  # Primary
# OR
BASELINE_LANGCHAIN_CHUTES_SEARCH_URL=https://search.chutes.ai  # Fallback
```

### 5. Configure Claude Code Agent

Add to Sandy bootstrap environment:
```bash
SERPER_API_KEY=${SERPER_API_KEY}
```

The Claude Code agent can then use tools that call the gateway's `/api/search/web` endpoint.

### 6. Update Agent System Prompt

**File: `baseline-agent-cli/agent-pack/prompts/system.md`**

Add guidance for web search:
```markdown
### Web Search
When you need to search the web for current information:
1. Use the `web_search` tool with your query
2. Results include title, URL, and snippet for each result
3. Cite sources when using information from search results
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SERPER_API_KEY` | Yes | Serper.dev API key for Google search |
| `SEARXNG_API_URL` | No | Optional SearXNG instance URL for fallback |

**Get Serper API Key:** https://serper.dev (free tier available)

---

## Testing

1. **Unit Test:** Mock Serper API response, verify parsing
2. **Integration Test:** Call `/api/search/web` with real query
3. **E2E Test:** Ask agent "Search the web for Python 3.12 release notes" and verify results

---

## Acceptance Criteria

- [ ] Web search returns results for valid queries
- [ ] Agent can perform web searches and cite sources
- [ ] Graceful error handling when API key missing
- [ ] Results include title, URL, and snippet
- [ ] Search works in both LangChain and Claude Code paths

NR_OF_TRIES: 1
