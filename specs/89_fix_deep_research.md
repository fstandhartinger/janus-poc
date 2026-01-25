# Spec 89: Fix Deep Research Feature

## Status: NOT STARTED

## Context / Why

The Deep Research feature in the Chat UI is completely broken. When users enable "Deep research" and send a message, they always receive the error:

```
Deep research unavailable; fallback failed.
```

This error originates from [gateway/janus_gateway/routers/research.py:170](gateway/janus_gateway/routers/research.py#L170) and indicates that:
1. The primary deep research request to chutes-search failed
2. The fallback request (regular search without deep research mode) also failed

## Current Implementation

### Flow
1. User enables "Deep research" toggle in ChatInput
2. ChatArea calls `streamDeepResearch()` from api.ts
3. Request goes to gateway `/api/research` endpoint
4. Gateway proxies to `chutes_search_url` (default: `https://search.chutes.ai/api/chat`)
5. Both primary and fallback requests fail → error message shown

### Relevant Files
- [ui/src/components/ChatInput.tsx](ui/src/components/ChatInput.tsx) - Deep research toggle UI
- [ui/src/components/ChatArea.tsx](ui/src/components/ChatArea.tsx) - Calls streamDeepResearch
- [ui/src/lib/api.ts](ui/src/lib/api.ts) - streamDeepResearch function
- [gateway/janus_gateway/routers/research.py](gateway/janus_gateway/routers/research.py) - Proxy endpoint
- [gateway/janus_gateway/config/settings.py](gateway/janus_gateway/config/settings.py) - chutes_search_url config

### Configuration
```python
chutes_search_url: str = Field(
    default="https://search.chutes.ai",
    description="Chutes search base URL",
)
chutes_api_key: str | None = Field(default=None, ...)
deep_research_timeout: int = Field(default=1200, ...)
```

## Investigation Required

1. **Verify chutes-search service status**
   - Is `https://search.chutes.ai` operational?
   - Check if it's deployed and responding

2. **Check API key configuration**
   - Is `CHUTES_API_KEY` set in Render environment variables for janus-gateway?
   - Is the key valid?

3. **Test the endpoint directly**
   ```bash
   curl -X POST https://search.chutes.ai/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"test"}],"focusMode":"webSearch"}'
   ```

4. **Check gateway logs**
   - Look for `deep_research_upstream_error` or `deep_research_fallback_failed` log entries
   - Check the actual error details

## Potential Fixes

### Option A: Fix chutes-search connectivity
If the search service is down or misconfigured:
- Verify the service is deployed and healthy
- Update the URL if it has changed
- Ensure API key is set

### Option B: Alternative search provider
If chutes-search is deprecated or unavailable:
- Integrate with an alternative search API (Brave Search, Perplexity, etc.)
- Use the existing Brave Search MCP tool if available

### Option C: Graceful degradation
If deep research can't be fixed immediately:
- Show a more helpful error message to users
- Disable the deep research toggle when the service is unavailable
- Add a health check endpoint to detect service availability

### Option D: Local research implementation
Implement deep research using:
- Web search via available APIs
- Content extraction and summarization
- Iterative research loops similar to existing patterns

## Acceptance Criteria

- [ ] Deep research feature works end-to-end
- [ ] User can enable deep research toggle and get meaningful results
- [ ] Error handling provides helpful feedback when service is temporarily unavailable
- [ ] Research progress stages display correctly during operation
- [ ] Sources are properly attributed in research results
- [ ] Works in both "light" and "max" research modes

## Testing

1. Enable deep research in chat UI
2. Submit a research query (e.g., "What are the latest developments in quantum computing?")
3. Verify:
   - Progress stages appear
   - Research completes successfully
   - Response includes sourced information
   - No error messages

## Related Specs

- `specs/44_deep_research_integration.md` - Original implementation
- `specs/45_browser_automation_screenshots.md` - Related browser features

## Notes

### URL Fix Applied
The gateway was updated to use `https://chutes-search.onrender.com` instead of the non-existent `https://search.chutes.ai`.

### Current Blocker: chutes-search service bug
The chutes-search service at `https://chutes-search.onrender.com` has a code bug:
```
TypeError: Cannot read properties of undefined (reading 'content')
```

This error occurs in `.next/server/app/api/chat/route.js` when processing chat requests. The service needs to be fixed in the `chutes-search` repository, not janus-poc.

### To Complete This Spec
1. Fix the bug in chutes-search service (separate repo)
2. Or implement alternative deep research using different provider (Brave Search, etc.)
