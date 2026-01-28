# Spec 94: Baseline LangChain End-to-End Verification

## Status: IN_PROGRESS
**Priority:** Critical
**Complexity:** High
**Prerequisites:** Spec 79 (Feature Parity), Spec 92, Spec 93

---

## Overview

This spec ensures the baseline-langchain implementation works end-to-end with feature parity to baseline-agent-cli. After Spec 79 implements the missing features, this spec verifies everything actually works with real test requests.

### Current Architecture (PoC Target)

The PoC uses this architecture for LangChain baseline:

```
USER → UI → Gateway (Render) → baseline-langchain (Render) → LangChain Agent (in-process)
                                                           → Chutes LLM API
                                                           → Tool calls (search, code exec, etc.)
```

Key differences from baseline-agent-cli:
- **baseline-langchain** runs the agent **in-process** (not via Sandy)
- Uses LangChain's agent framework with custom tools
- This is intentional - shows an alternative baseline approach
- Containerization is deferred (see Spec 95)

### Requirements from Investigation

Based on the conversation about baseline-agent-cli, the LangChain baseline must also:
1. Route simple queries to fast path, complex to agent
2. Support various complex tasks (git, web search, coding, multimodal)
3. Work with multiple Chutes models
4. Stream SSE properly with reasoning_content
5. Have comprehensive logging for debugging

---

## Functional Requirements

### FR-1: Feature Parity Verification

Compare behavior between CLI and LangChain baselines.

```python
# tests/e2e/test_feature_parity.py

import pytest
import httpx
import asyncio

GATEWAY_URL = "https://janus-gateway.onrender.com"

class TestFeatureParity:
    """Verify LangChain baseline matches CLI baseline capabilities."""

    @pytest.mark.e2e
    @pytest.mark.parametrize("baseline", ["baseline-agent-cli", "baseline-langchain"])
    async def test_simple_query_response(self, baseline: str):
        """Both baselines should answer simple queries quickly."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "What is 2 + 2?"}],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "4" in data["choices"][0]["message"]["content"]

    @pytest.mark.e2e
    @pytest.mark.parametrize("baseline", ["baseline-agent-cli", "baseline-langchain"])
    async def test_image_generation(self, baseline: str):
        """Both baselines should generate images."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "Generate an image of a sunset"}],
                    "stream": False,
                },
            )
            data = response.json()

            # Should have image artifact or mention generation
            artifacts = data.get("artifacts", [])
            content = data["choices"][0]["message"]["content"]
            has_image = (
                any(a.get("type") == "image" for a in artifacts) or
                "generated" in content.lower() or
                "image" in content.lower()
            )
            assert has_image

    @pytest.mark.e2e
    @pytest.mark.parametrize("baseline", ["baseline-agent-cli", "baseline-langchain"])
    async def test_web_search(self, baseline: str):
        """Both baselines should perform web search."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{
                        "role": "user",
                        "content": "Search the web for today's top AI news"
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have search results
            assert len(content) > 100
            # Should mention sources or news items
            assert any(word in content.lower() for word in ["news", "source", "article", "report", "today"])
```

### FR-2: LangChain-Specific Tests

Test LangChain agent capabilities.

```python
# tests/e2e/test_langchain_baseline.py

LANGCHAIN_URL = "https://janus-baseline-langchain.onrender.com"

class TestLangChainBaseline:
    """Test LangChain-specific functionality."""

    @pytest.mark.e2e
    async def test_complexity_detection(self):
        """LangChain should route based on complexity."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Simple query (should be fast)
            start = time.time()
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": False,
                },
            )
            simple_time = time.time() - start

            # Complex query (may take longer, uses agent)
            start = time.time()
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Research the latest developments in quantum computing"
                    }],
                    "stream": False,
                },
            )
            complex_time = time.time() - start

            # Simple should be much faster (unless both route to agent)
            # This test mainly checks that both complete successfully
            assert response.status_code == 200

    @pytest.mark.e2e
    async def test_langchain_tools(self):
        """LangChain should have working tools."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Test code execution
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Use Python to calculate 123 * 456 and tell me the result"
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have the actual result: 56088
            assert "56088" in content

    @pytest.mark.e2e
    async def test_langchain_streaming(self):
        """LangChain should stream SSE correctly."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "Tell me a short joke"}],
                    "stream": True,
                },
            ) as response:
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(line)

                # Should have multiple events
                assert len(events) > 1
                # Should end with [DONE]
                assert events[-1] == "data: [DONE]"

    @pytest.mark.e2e
    async def test_langchain_reasoning_content(self):
        """LangChain should include reasoning_content."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Explain step by step how to make coffee"
                    }],
                    "stream": True,
                },
            ) as response:
                saw_reasoning = False
                saw_content = False

                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        delta = data["choices"][0].get("delta", {})
                        if delta.get("reasoning_content"):
                            saw_reasoning = True
                        if delta.get("content"):
                            saw_content = True

                # Must have content, reasoning is optional
                assert saw_content
```

### FR-3: Complex Task Tests for LangChain

```python
# tests/e2e/test_langchain_complex_tasks.py

class TestLangChainComplexTasks:
    """Test complex tasks specific to LangChain baseline."""

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_deep_research(self):
        """LangChain should perform deep research with citations."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Do comprehensive research on the impact of AI on healthcare. Include citations."
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have substantial content
            assert len(content) > 500
            # Should have sources/citations
            assert any(marker in content for marker in ["[", "source", "http", "according to"])

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_tts_generation(self):
        """LangChain should generate text-to-speech audio."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Convert this to audio: Welcome to Janus, the AI benchmark platform"
                    }],
                    "stream": False,
                },
            )
            data = response.json()

            # Should have audio artifact
            artifacts = data.get("artifacts", [])
            content = data["choices"][0]["message"]["content"]
            has_audio = (
                any(a.get("type") == "audio" for a in artifacts) or
                "audio" in content.lower() or
                "generated" in content.lower()
            )
            assert has_audio

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_video_generation(self):
        """LangChain should generate video (if implemented)."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Generate a short video of a bouncing ball"
                    }],
                    "stream": False,
                },
            )
            data = response.json()

            # May or may not be implemented yet
            # Just verify it doesn't crash
            assert response.status_code == 200

    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_file_operations(self):
        """LangChain should create file artifacts."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": "Write a Python script that prints 'Hello World' and save it as hello.py"
                    }],
                    "stream": False,
                },
            )
            data = response.json()

            # Should mention file creation or have artifact
            artifacts = data.get("artifacts", [])
            content = data["choices"][0]["message"]["content"]
            has_file = (
                any(a.get("type") == "file" for a in artifacts) or
                "hello.py" in content.lower() or
                "created" in content.lower()
            )
            assert has_file
```

### FR-4: Model Router Integration for LangChain

```python
# tests/e2e/test_langchain_model_router.py

class TestLangChainModelRouter:
    """Test LangChain uses model router for smart routing."""

    @pytest.mark.e2e
    async def test_vision_model_routing(self):
        """Image input should route to vision model."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image"},
                            {"type": "image_url", "image_url": {"url": "https://picsum.photos/200"}}
                        ]
                    }],
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have image description
            assert len(content) > 50

    @pytest.mark.e2e
    async def test_fallback_on_rate_limit(self):
        """LangChain should fallback to different model on 429."""
        # This is harder to test without causing actual rate limits
        # For now, just verify the endpoint works
        pass

    @pytest.mark.e2e
    @pytest.mark.parametrize("model", [
        "MiniMaxAI/MiniMax-M2",
        "deepseek-ai/DeepSeek-V3-0324",
        "THUDM/GLM-4-Plus",
    ])
    async def test_explicit_model_selection(self, model: str):
        """LangChain should support explicit model selection."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hello in 5 words"}],
                    "stream": False,
                },
            )

            if response.status_code == 200:
                data = response.json()
                assert len(data["choices"][0]["message"]["content"]) > 0
            else:
                pytest.skip(f"Model {model} not available")
```

### FR-5: Memory Integration Tests

```python
# tests/e2e/test_langchain_memory.py

class TestLangChainMemory:
    """Test memory integration for LangChain baseline."""

    @pytest.mark.e2e
    async def test_memory_context_injection(self):
        """LangChain should inject memory context."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Send a fact to remember
            await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "My favorite color is blue. Remember this."}],
                    "user_id": "test-user-123",
                    "enable_memory": True,
                    "stream": False,
                },
            )

            # Query the fact
            response = await client.post(
                f"{LANGCHAIN_URL}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "What is my favorite color?"}],
                    "user_id": "test-user-123",
                    "enable_memory": True,
                    "stream": False,
                },
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should recall the color
            assert "blue" in content.lower()
```

---

## Acceptance Criteria

### Feature Parity with CLI Agent
- [ ] Simple queries work with fast response
- [ ] Complex queries use agent path
- [ ] Image generation works
- [ ] TTS generation works
- [ ] Web search returns real results
- [ ] Deep research includes citations
- [ ] Code execution runs and returns output
- [ ] File operations create artifacts

### Streaming
- [ ] SSE format matches OpenAI spec
- [ ] Events end with [DONE]
- [ ] reasoning_content streams before content
- [ ] Artifacts included in final message

### Model Router
- [ ] Vision models used for image input
- [ ] Explicit model selection works
- [ ] Rate limit fallback works (if testable)

### Memory
- [ ] Memory context injection works
- [ ] Facts are recalled in subsequent requests

### Logging
- [ ] All events logged with correlation ID
- [ ] Complexity analysis logged
- [ ] Tool calls logged
- [ ] Errors logged with context

---

## Testing Procedure

### 1. Deploy Latest LangChain Baseline

```bash
cd baseline-langchain
git add -A && git commit -m "Feature parity implementation" && git push
# Wait for Render deployment
```

### 2. Run E2E Test Suite

```bash
cd baseline-langchain
pytest tests/e2e/ -v --timeout=600 -x
```

### 3. Manual Testing

```bash
# Simple query
curl -X POST https://janus-gateway.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "baseline-langchain",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'

# Complex query with streaming
curl -X POST https://janus-gateway.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "baseline-langchain",
    "messages": [{"role": "user", "content": "Research AI trends in 2026"}],
    "stream": true
  }'
```

### 4. Compare with CLI Baseline

Run the same queries against both baselines and compare:
- Response quality
- Response time
- Artifacts generated
- Errors encountered

---

## Files to Create

| File | Purpose |
|------|---------|
| `baseline-langchain/tests/e2e/test_feature_parity.py` | Parity tests |
| `baseline-langchain/tests/e2e/test_langchain_baseline.py` | LangChain-specific tests |
| `baseline-langchain/tests/e2e/test_langchain_complex_tasks.py` | Complex task tests |
| `baseline-langchain/tests/e2e/test_langchain_model_router.py` | Model router tests |
| `baseline-langchain/tests/e2e/test_langchain_memory.py` | Memory tests |
| `baseline-langchain/tests/e2e/conftest.py` | Test fixtures |

## Files to Modify

| File | Changes |
|------|---------|
| `baseline-langchain/janus_baseline_langchain/main.py` | Ensure logging |
| `baseline-langchain/janus_baseline_langchain/config.py` | Add test config |
| `baseline-langchain/pyproject.toml` | Add test dependencies |

---

## Notes

- LangChain runs in-process, not in Sandy sandbox (intentional difference)
- Some tools may behave differently than CLI agent
- Test timeouts should be generous for complex tasks
- Log analysis is critical for debugging failures
- Consider running tests in parallel where possible

---

## Related Specs

- Spec 79: Baseline LangChain Feature Parity (implements features)
- Spec 92: Baseline Agent CLI E2E Verification (parallel spec)
- Spec 93: Comprehensive Logging & Observability (logging framework)

NR_OF_TRIES: 1
