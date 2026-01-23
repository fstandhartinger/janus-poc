# Spec 44: Deep Research Integration

## Status: DRAFT

## Context / Why

The chutes-search project implements sophisticated "Deep Research" - an 8-stage pipeline that:
1. Searches the web for sources
2. Creates a Sandy sandbox with Playwright
3. Crawls pages with a headless browser
4. Synthesizes findings with AI
5. Generates a comprehensive, cited report

The Janus agent should be able to leverage this capability for tasks requiring thorough research.

## Goals

- Integrate deep research as an agent capability
- Stream progress events back to the user
- Support both "light" and "max" research modes
- Return properly cited, comprehensive reports
- Reuse existing chutes-search infrastructure

## Non-Goals

- Reimplementing deep research from scratch
- Replacing web search for simple queries
- Real-time continuous research

## Functional Requirements

### FR-1: Deep Research Client Library

```python
# agent-pack/lib/deep_research.py
"""Deep research client for Janus agents."""

import os
import json
import httpx
from typing import AsyncIterator, Optional
from dataclasses import dataclass


@dataclass
class ResearchProgress:
    """Progress update during research."""
    stage: str
    status: str  # pending, running, complete, error
    detail: str
    percent: float


@dataclass
class ResearchSource:
    """A source used in research."""
    title: str
    url: str
    snippet: str


@dataclass
class ResearchResult:
    """Complete research result."""
    report: str
    sources: list[ResearchSource]
    query: str
    mode: str
    duration_seconds: float


class DeepResearchClient:
    """Client for chutes-search deep research API."""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
    ):
        self.base_url = base_url or os.environ.get(
            "CHUTES_SEARCH_URL",
            "https://search.chutes.ai"
        )
        self.api_key = api_key or os.environ.get("CHUTES_API_KEY")

    async def research(
        self,
        query: str,
        mode: str = "light",  # "light" or "max"
        optimization: str = "balanced",  # "speed", "balanced", "quality"
        on_progress: callable = None,
    ) -> ResearchResult:
        """
        Perform deep research on a topic.

        Args:
            query: Research question or topic
            mode: "light" (faster, 10 sources) or "max" (thorough, 18 sources)
            optimization: "speed", "balanced", or "quality"
            on_progress: Optional callback for progress updates

        Returns:
            ResearchResult with report and sources
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=1200) as client:  # 20 min timeout
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "messages": [{"role": "user", "content": query}],
                    "deepResearchMode": mode,
                    "optimizationMode": optimization,
                    "focusMode": "webSearch",
                },
                headers=headers,
            ) as response:
                response.raise_for_status()

                report_chunks = []
                sources = []
                start_time = None

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type")

                    if event_type == "progress":
                        if on_progress:
                            progress = ResearchProgress(
                                stage=data["data"].get("label", ""),
                                status=data["data"].get("status", ""),
                                detail=data["data"].get("detail", ""),
                                percent=data["data"].get("percent", 0),
                            )
                            on_progress(progress)

                    elif event_type == "sources":
                        for source_list in data.get("data", []):
                            for src in source_list:
                                sources.append(ResearchSource(
                                    title=src.get("metadata", {}).get("title", ""),
                                    url=src.get("metadata", {}).get("url", ""),
                                    snippet=src.get("pageContent", "")[:200],
                                ))

                    elif event_type == "response":
                        report_chunks.append(data.get("data", ""))

                return ResearchResult(
                    report="".join(report_chunks),
                    sources=sources,
                    query=query,
                    mode=mode,
                    duration_seconds=0,  # Could track this
                )

    async def research_stream(
        self,
        query: str,
        mode: str = "light",
    ) -> AsyncIterator[str]:
        """
        Stream research progress and results.

        Yields formatted strings suitable for display.
        """
        def format_progress(p: ResearchProgress) -> str:
            icons = {
                "pending": "⏳",
                "running": "🔄",
                "complete": "✅",
                "error": "❌",
            }
            icon = icons.get(p.status, "•")
            return f"{icon} {p.stage}: {p.detail}"

        progress_updates = []

        def on_progress(p: ResearchProgress):
            progress_updates.append(format_progress(p))

        result = await self.research(query, mode, on_progress=on_progress)

        # Yield progress first
        for update in progress_updates:
            yield update + "\n"

        # Then yield the report
        yield "\n---\n\n"
        yield result.report

        # Then sources
        yield "\n\n---\n\n## Sources\n\n"
        for i, src in enumerate(result.sources, 1):
            yield f"{i}. [{src.title}]({src.url})\n"


# Convenience function
async def deep_research(
    query: str,
    mode: str = "light",
    verbose: bool = True,
) -> str:
    """
    Perform deep research and return formatted report.

    Args:
        query: What to research
        mode: "light" or "max"
        verbose: Print progress updates

    Returns:
        Markdown-formatted research report with citations
    """
    client = DeepResearchClient()

    output = []

    if verbose:
        print(f"🔬 Starting deep research ({mode} mode)...")
        print(f"📋 Query: {query}\n")

    async for chunk in client.research_stream(query, mode):
        if verbose:
            print(chunk, end="", flush=True)
        output.append(chunk)

    return "".join(output)
```

### FR-2: Gateway Proxy Endpoint

Add a gateway endpoint to proxy research requests:

```python
# gateway/janus_gateway/routers/research.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api", tags=["research"])

CHUTES_SEARCH_URL = "https://search.chutes.ai"


class ResearchRequest(BaseModel):
    query: str
    mode: str = "light"  # light or max
    optimization: str = "balanced"


@router.post("/research")
async def deep_research(request: ResearchRequest):
    """
    Proxy deep research requests to chutes-search.

    Streams SSE events for progress and results.
    """
    async def stream_research():
        async with httpx.AsyncClient(timeout=1200) as client:
            async with client.stream(
                "POST",
                f"{CHUTES_SEARCH_URL}/api/chat",
                json={
                    "messages": [{"role": "user", "content": request.query}],
                    "deepResearchMode": request.mode,
                    "optimizationMode": request.optimization,
                    "focusMode": "webSearch",
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        stream_research(),
        media_type="text/event-stream",
    )
```

### FR-3: Frontend Research Progress Component

```tsx
// ui/src/components/DeepResearchProgress.tsx

import { useState, useEffect } from 'react';
import { CheckCircle, Circle, Loader2, XCircle } from 'lucide-react';

interface ResearchStage {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  detail?: string;
}

const STAGES = [
  { id: '1', label: 'Finding Sources' },
  { id: '2', label: 'Preparing Sandbox' },
  { id: '3', label: 'Installing Browser' },
  { id: '4', label: 'Launching Browser' },
  { id: '5', label: 'Crawling Pages' },
  { id: '6', label: 'Synthesizing Notes' },
  { id: '7', label: 'Drafting Report' },
  { id: '8', label: 'Cleaning Up' },
];

interface DeepResearchProgressProps {
  stages: ResearchStage[];
  isActive: boolean;
}

export function DeepResearchProgress({ stages, isActive }: DeepResearchProgressProps) {
  if (!isActive) return null;

  return (
    <div className="p-4 rounded-lg border border-moss/30 bg-moss/5">
      <div className="text-sm font-semibold text-moss mb-3">
        Deep Research in Progress
      </div>
      <div className="space-y-2">
        {STAGES.map((stage, index) => {
          const stageData = stages.find(s => s.label === stage.label);
          const status = stageData?.status || 'pending';

          return (
            <div key={stage.id} className="flex items-center gap-2 text-sm">
              {status === 'complete' && (
                <CheckCircle className="w-4 h-4 text-moss" />
              )}
              {status === 'running' && (
                <Loader2 className="w-4 h-4 text-moss animate-spin" />
              )}
              {status === 'pending' && (
                <Circle className="w-4 h-4 text-ink-500" />
              )}
              {status === 'error' && (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              <span className={status === 'running' ? 'text-moss' : 'text-ink-400'}>
                {stage.label}
              </span>
              {stageData?.detail && (
                <span className="text-xs text-ink-500">
                  {stageData.detail}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### FR-4: System Prompt Addition

```markdown
### 🔬 Deep Research

For questions requiring thorough investigation, use deep research:

```python
from lib.deep_research import deep_research

# Light mode (faster, ~2-5 minutes)
report = await deep_research(
    "What are the latest developments in quantum computing?",
    mode="light",
)

# Max mode (thorough, ~10-18 minutes)
report = await deep_research(
    "Compare AI regulation approaches across US, EU, and China",
    mode="max",
)

print(report)  # Includes citations [1], [2], etc.
```

**When to use deep research:**
- Complex topics requiring multiple sources
- Current events or recent developments
- Comparative analysis
- Technical deep-dives

**When NOT to use:**
- Simple factual questions
- Code generation tasks
- Personal opinions
```

## Non-Functional Requirements

### NFR-1: Performance

- Light mode: 2-5 minutes
- Max mode: 10-18 minutes
- Progress updates every 1-2 seconds

### NFR-2: Reliability

- Graceful fallback to regular search if deep research fails
- Partial results returned on timeout
- Proper error messages

### NFR-3: Quality

- All statements cite sources
- Sources are ranked by relevance
- Report follows consistent structure

## Acceptance Criteria

- [ ] Deep research client library works
- [ ] Progress streaming to frontend
- [ ] Light and max modes functional
- [ ] Citations properly formatted
- [ ] Gateway proxy endpoint works
- [ ] Progress UI component displays correctly
- [ ] Timeout handling works

## Files to Create/Modify

```
baseline-agent-cli/
└── agent-pack/
    └── lib/
        └── deep_research.py     # NEW

gateway/
└── janus_gateway/
    └── routers/
        ├── __init__.py          # MODIFY - Include research router
        └── research.py          # NEW

ui/
└── src/
    └── components/
        └── DeepResearchProgress.tsx  # NEW
```

## Related Specs

- `specs/41_enhanced_agent_system_prompt.md` - Agent capabilities
- `specs/45_browser_automation.md` - Browser control
