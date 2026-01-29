# Spec 102: Core Demo Use Cases - End-to-End Quality

## Status: COMPLETE

## Context / Why

To demonstrate Janus's value proposition, we need 3-4 core use cases that work flawlessly. These should showcase:
1. The fast path (simple queries)
2. The agent path (complex agentic tasks)
3. Multimodal capabilities

If these demos fail or are flaky, the entire pitch fails.

## Core Demo Use Cases

### Demo 1: Simple Question (Fast Path)
**Prompt:** "Explain why it rains"
**Expected:** Direct LLM response, <2s latency, no tool use
**Tests:** Complexity detection correctly routes to fast path

### Demo 2: Repository Clone & Summarize (Agentic)
**Prompt:** "Clone the https://github.com/anthropics/anthropic-cookbook repository and give me a summary of what it contains"
**Expected:**
- Agent spawns in sandbox
- Git clone executes
- Files are listed/read
- Summary is generated
- Reasoning tokens stream throughout
- Completes in <2 minutes

### Demo 3: Web Research Report (Research)
**Prompt:** "Search the web for the latest developments in quantum computing in 2026 and write me a brief report with sources"
**Expected:**
- Web search tool is called
- Multiple sources are consulted
- Report includes citations/links
- Structured output (headers, bullets)
- Completes in <60 seconds

### Demo 4: Image Generation (Multimodal)
**Prompt:** "Generate an image of a futuristic city with flying cars at sunset"
**Expected:**
- Image generation tool is called
- Image is returned inline or as artifact
- Descriptive text accompanies the image
- Completes in <30 seconds

## Functional Requirements

### FR-1: Automated Test Suite for Demos

```python
# tests/e2e/test_core_demos.py

import pytest
import httpx
import time
import json

GATEWAY_URL = "http://localhost:8000"
BASELINE_CLI_URL = "http://localhost:8081"

class TestCoreDemos:
    """End-to-end tests for core demo use cases."""

    @pytest.mark.asyncio
    async def test_demo_1_simple_question_fast_path(self):
        """Simple questions should use fast path with low latency."""
        async with httpx.AsyncClient(timeout=30) as client:
            start = time.time()

            response = await client.post(
                f"{BASELINE_CLI_URL}/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{"role": "user", "content": "Explain why it rains"}],
                    "stream": True,
                },
            )

            assert response.status_code == 200

            content = ""
            reasoning = ""
            first_token_time = None

            async for line in response.aiter_lines():
                if first_token_time is None and line.startswith("data: "):
                    first_token_time = time.time() - start

                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content += delta.get("content", "")
                    reasoning += delta.get("reasoning_content", "")

            elapsed = time.time() - start

            # Assertions
            assert first_token_time < 2.0, f"First token too slow: {first_token_time}s"
            assert elapsed < 10.0, f"Total response too slow: {elapsed}s"
            assert "water" in content.lower() or "evapor" in content.lower()
            assert len(reasoning) == 0, "Fast path should not have reasoning tokens"

            print(f"✅ Demo 1 passed: {elapsed:.1f}s, TTFT: {first_token_time:.2f}s")

    @pytest.mark.asyncio
    async def test_demo_2_repo_clone_summarize(self):
        """Clone repo and summarize - full agentic flow."""
        async with httpx.AsyncClient(timeout=300) as client:
            start = time.time()

            response = await client.post(
                f"{BASELINE_CLI_URL}/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{
                        "role": "user",
                        "content": "Clone the https://github.com/anthropics/anthropic-cookbook repository and give me a summary of what it contains"
                    }],
                    "stream": True,
                },
            )

            assert response.status_code == 200

            content = ""
            reasoning = ""

            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content += delta.get("content", "")
                    reasoning += delta.get("reasoning_content", "")

            elapsed = time.time() - start

            # Assertions
            assert elapsed < 180, f"Took too long: {elapsed}s"
            assert len(reasoning) > 100, "Should have reasoning tokens from agent"
            assert "anthropic" in content.lower() or "cookbook" in content.lower()
            assert any(word in content.lower() for word in ["example", "notebook", "tutorial", "guide"])

            print(f"✅ Demo 2 passed: {elapsed:.1f}s, reasoning: {len(reasoning)} chars")

    @pytest.mark.asyncio
    async def test_demo_3_web_research_report(self):
        """Web search and research report generation."""
        async with httpx.AsyncClient(timeout=120) as client:
            start = time.time()

            response = await client.post(
                f"{BASELINE_CLI_URL}/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{
                        "role": "user",
                        "content": "Search the web for the latest developments in quantum computing in 2026 and write me a brief report with sources"
                    }],
                    "stream": True,
                },
            )

            assert response.status_code == 200

            content = ""
            reasoning = ""

            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content += delta.get("content", "")
                    reasoning += delta.get("reasoning_content", "")

            elapsed = time.time() - start

            # Assertions
            assert elapsed < 90, f"Took too long: {elapsed}s"
            assert "quantum" in content.lower()
            # Should have sources/links
            assert "http" in content or "source" in content.lower() or "[" in content
            assert len(content) > 500, "Report should be substantial"

            print(f"✅ Demo 3 passed: {elapsed:.1f}s, content: {len(content)} chars")

    @pytest.mark.asyncio
    async def test_demo_4_image_generation(self):
        """Generate an image from text prompt."""
        async with httpx.AsyncClient(timeout=60) as client:
            start = time.time()

            response = await client.post(
                f"{BASELINE_CLI_URL}/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{
                        "role": "user",
                        "content": "Generate an image of a futuristic city with flying cars at sunset"
                    }],
                    "stream": True,
                },
            )

            assert response.status_code == 200

            content = ""
            has_image = False

            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    chunk_content = delta.get("content", "")
                    content += chunk_content

                    # Check for image indicators
                    if any(x in chunk_content for x in ["![", "data:image", "/api/artifacts", ".png", ".jpg"]):
                        has_image = True

            elapsed = time.time() - start

            # Assertions
            assert elapsed < 45, f"Took too long: {elapsed}s"
            assert has_image, "Response should contain an image"

            print(f"✅ Demo 4 passed: {elapsed:.1f}s, has image: {has_image}")


class TestCoreDemosViaGateway:
    """Same tests but through the gateway (full stack)."""

    @pytest.mark.asyncio
    async def test_gateway_demo_1_simple(self):
        """Simple question through gateway."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": "baseline-agent-cli",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": True,
                },
            )
            assert response.status_code == 200

            content = ""
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content += delta.get("content", "")

            assert "4" in content


class TestCoreDemosViaUI:
    """Tests that verify the demos work end-to-end via the actual UI."""

    # These would use Playwright to actually interact with the chat UI
    # Implemented in spec 103
    pass
```

### FR-2: Reliability Improvements for Demo 2 (Repo Clone)

```python
# In baseline-agent-cli - ensure repo operations work reliably

# 1. Increase timeouts for git operations
SANDY_GIT_TIMEOUT = 120  # 2 minutes for large repos

# 2. Add progress streaming during clone
async def stream_git_progress(sandbox_id: str):
    """Stream progress during git operations."""
    yield create_reasoning_chunk("Cloning repository...")
    # ... actual clone
    yield create_reasoning_chunk("Repository cloned. Analyzing contents...")

# 3. Handle common failures
REPO_ERROR_MESSAGES = {
    "repository not found": "The repository URL appears to be invalid or private.",
    "timeout": "The repository is taking too long to clone. It may be too large.",
    "permission denied": "Unable to access this repository. It may be private.",
}
```

### FR-3: Reliability Improvements for Demo 3 (Research)

```python
# Ensure web search + report generation is reliable

# 1. Use multiple search sources if one fails
async def robust_web_search(query: str) -> list[SearchResult]:
    """Search with fallback."""
    try:
        return await primary_search(query)  # e.g., Brave
    except Exception:
        return await fallback_search(query)  # e.g., DuckDuckGo

# 2. Validate search results before using
def filter_valid_results(results: list[SearchResult]) -> list[SearchResult]:
    """Filter out broken/irrelevant results."""
    return [r for r in results if r.url and r.snippet and len(r.snippet) > 50]

# 3. Structure the report output
RESEARCH_REPORT_TEMPLATE = """
## {topic}

### Key Findings
{findings}

### Sources
{sources}
"""
```

### FR-4: Reliability Improvements for Demo 4 (Image)

```python
# Ensure image generation works reliably

# 1. Validate image generation response
async def generate_image_with_validation(prompt: str) -> str:
    """Generate image with validation."""
    result = await chutes_image_api.generate(prompt)

    if not result or not result.url:
        raise ImageGenerationError("Image generation failed")

    # Verify URL is accessible
    async with httpx.AsyncClient() as client:
        response = await client.head(result.url)
        if response.status_code != 200:
            raise ImageGenerationError("Generated image URL is not accessible")

    return result.url

# 2. Format image in response properly
def format_image_response(url: str, prompt: str) -> str:
    """Format image as markdown."""
    return f"Here's the generated image:\n\n![{prompt}]({url})\n"
```

## Acceptance Criteria

- [ ] Demo 1 (simple question) completes in <2s TTFT, <10s total
- [ ] Demo 2 (repo clone) completes in <180s with reasoning tokens
- [ ] Demo 3 (research) completes in <90s with sources
- [ ] Demo 4 (image) completes in <45s with visible image
- [ ] All demos pass 95%+ of the time (not flaky)
- [ ] All demos work through gateway (not just direct baseline)
- [ ] All demos render correctly in chat UI

## Files to Create/Modify

```
tests/
└── e2e/
    └── test_core_demos.py  # NEW

baseline-agent-cli/janus_baseline_agent_cli/
├── services/
│   ├── git_handler.py      # MODIFY: Reliability
│   └── search_handler.py   # MODIFY: Reliability
└── main.py                 # MODIFY: Timeout configs

baseline-langchain/janus_baseline_langchain/
└── tools/
    └── ...                 # MODIFY per spec 101
```

## Running the Tests

```bash
# Run core demo tests
pytest tests/e2e/test_core_demos.py -v --timeout=300

# Run with output for debugging
pytest tests/e2e/test_core_demos.py -v -s --timeout=300

# Run specific demo
pytest tests/e2e/test_core_demos.py::TestCoreDemos::test_demo_2_repo_clone_summarize -v
```

## Related Specs

- Spec 100: Long Agentic Task Reliability
- Spec 101: Baseline LangChain Full Parity
- Spec 103: Demo Prompts in Chat UI

NR_OF_TRIES: 2
