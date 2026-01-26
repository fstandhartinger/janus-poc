# Spec 101: Integration Testing Suite

## Status: TODO

**Priority:** High
**Complexity:** High
**Prerequisites:** Spec 100 (Unit Tests)

---

## Overview

Integration tests verify that components work together correctly. Unlike unit tests, these tests:

1. Test real interactions between services
2. May use real databases/APIs (or controlled test instances)
3. Test streaming, timeouts, and error propagation
4. Can run against local or deployed environments

**Important:** If any tests fail during implementation, FIX the underlying code to make them pass.

---

## Test Environment Configuration

### Configuration File: `tests/config.py`

```python
import os
from pydantic_settings import BaseSettings

class TestConfig(BaseSettings):
    """Test configuration for local vs deployed testing."""

    # Test mode: "local" or "deployed"
    test_mode: str = os.getenv("TEST_MODE", "local")

    # Local URLs
    gateway_local: str = "http://localhost:8000"
    baseline_cli_local: str = "http://localhost:8001"
    baseline_langchain_local: str = "http://localhost:8002"
    ui_local: str = "http://localhost:3000"

    # Deployed URLs
    gateway_deployed: str = "https://janus-gateway-bqou.onrender.com"
    baseline_cli_deployed: str = "https://janus-baseline-agent.onrender.com"
    baseline_langchain_deployed: str = "https://janus-baseline-langchain.onrender.com"
    ui_deployed: str = "https://janus.rodeo"
    memory_service_deployed: str = "https://janus-memory-service.onrender.com"

    # Auth - for tests requiring login
    chutes_fingerprint: str = os.getenv("CHUTES_FINGERPRINT", "")
    chutes_api_key: str = os.getenv("CHUTES_API_KEY", "")

    # Timeouts (seconds)
    health_timeout: int = 10
    simple_request_timeout: int = 60
    complex_request_timeout: int = 300
    streaming_timeout: int = 300

    def get_url(self, service: str) -> str:
        """Get URL for a service based on test mode."""
        suffix = "deployed" if self.test_mode == "deployed" else "local"
        return getattr(self, f"{service}_{suffix}")

config = TestConfig()
```

---

## Part 1: Gateway Integration Tests

### Location: `tests/integration/test_gateway_integration.py`

```python
import pytest
import httpx
import json
import time
from tests.config import config

class TestGatewayHealth:
    """Test gateway health and readiness."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Gateway /health returns 200."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["ok", "healthy"]

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self):
        """OpenAPI docs endpoint works."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/docs")
            assert response.status_code == 200


class TestModelsEndpoint:
    """Test /v1/models endpoint."""

    @pytest.mark.asyncio
    async def test_list_models(self):
        """List available models."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/v1/models")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) > 0

            # Check model structure
            model = data["data"][0]
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"

    @pytest.mark.asyncio
    async def test_models_include_baselines(self):
        """Both baseline models are listed."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/v1/models")
            data = response.json()
            model_ids = [m["id"] for m in data["data"]]

            # At least one baseline should exist
            assert any("baseline" in mid.lower() for mid in model_ids)


class TestChatCompletionsNonStreaming:
    """Test non-streaming chat completions."""

    @pytest.mark.asyncio
    async def test_simple_chat_completion(self):
        """Simple chat completion returns valid response."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Say hello in exactly one word"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert len(data["choices"][0]["message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self):
        """Chat with system message works."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "system", "content": "You are a pirate. Respond like one."},
                        {"role": "user", "content": "Hello"},
                    ],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            # Response should be pirate-like (flexible check)
            assert len(content) > 0

    @pytest.mark.asyncio
    async def test_chat_with_temperature(self):
        """Temperature parameter is accepted."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                    "temperature": 0.0,
                }
            )
            assert response.status_code == 200


class TestChatCompletionsStreaming:
    """Test streaming chat completions."""

    @pytest.mark.asyncio
    async def test_streaming_simple_query(self):
        """Streaming simple query returns SSE chunks."""
        url = config.get_url("gateway")
        chunks = []
        content_parts = []

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Count from 1 to 5"}],
                    "stream": True,
                }
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            chunks.append({"done": True})
                        else:
                            try:
                                chunk = json.loads(data)
                                chunks.append(chunk)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    content_parts.append(delta["content"])
                            except json.JSONDecodeError:
                                pass

        assert len(chunks) > 0
        assert any(c.get("done") for c in chunks)  # Has [DONE] marker
        full_content = "".join(content_parts)
        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_streaming_time_to_first_token(self):
        """Time to first token is reasonable (<5s for simple query)."""
        url = config.get_url("gateway")
        start_time = time.time()
        first_token_time = None

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line[6:] != "[DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                                first_token_time = time.time()
                                break
                        except json.JSONDecodeError:
                            pass

        if first_token_time:
            ttft = first_token_time - start_time
            assert ttft < 5.0, f"TTFT too slow: {ttft:.2f}s"

    @pytest.mark.asyncio
    async def test_streaming_no_large_gaps(self):
        """No gaps >5s between chunks during streaming."""
        url = config.get_url("gateway")
        last_time = time.time()
        max_gap = 0

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Tell me a short story"}],
                    "stream": True,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        now = time.time()
                        gap = now - last_time
                        max_gap = max(max_gap, gap)
                        last_time = now

        assert max_gap < 5.0, f"Max gap too large: {max_gap:.2f}s"


class TestChatCompletionsComplex:
    """Test complex requests that may use agent path."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_code_generation(self):
        """Code generation request works."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Write a Python function that adds two numbers"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "def" in content or "function" in content.lower()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_web_search_query(self):
        """Web search request works (if agent supports it)."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "What is today's date?"}],
                    "stream": False,
                }
            )
            # Should succeed regardless of whether web search is invoked
            assert response.status_code == 200


class TestMultimodalRequests:
    """Test requests with image content."""

    @pytest.mark.asyncio
    async def test_image_understanding(self):
        """Request with image is accepted."""
        url = config.get_url("gateway")
        # 1x1 transparent PNG
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What do you see in this image?"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_b64}"}}
                        ]
                    }],
                    "stream": False,
                }
            )
            assert response.status_code == 200


class TestTranscriptionProxy:
    """Test transcription proxy endpoint."""

    @pytest.mark.asyncio
    async def test_transcription_health(self):
        """Transcription health endpoint works."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/api/transcribe/health")
            # May be 200 or 503 depending on configuration
            assert response.status_code in [200, 503, 404]

    @pytest.mark.asyncio
    @pytest.mark.skipif(not config.chutes_api_key, reason="Requires CHUTES_API_KEY")
    async def test_transcription_request(self):
        """Transcription endpoint processes audio."""
        url = config.get_url("gateway")
        # Small valid audio file would be needed for real test
        # This is a structural test
        pass


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_model_error(self):
        """Invalid model returns appropriate error."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "nonexistent-model-12345",
                    "messages": [{"role": "user", "content": "Hi"}],
                }
            )
            assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_missing_messages_error(self):
        """Missing messages returns validation error."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={"model": "baseline-cli-agent"}
            )
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_malformed_json_error(self):
        """Malformed JSON returns error."""
        url = config.get_url("gateway")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                content="{invalid json}",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code in [400, 422]
```

---

## Part 2: Baseline Integration Tests

### Location: `tests/integration/test_baseline_cli_integration.py`

```python
import pytest
import httpx
import json
from tests.config import config

class TestBaselineCLIHealth:
    """Test baseline CLI health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Baseline CLI /health returns 200."""
        url = config.get_url("baseline_cli")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200


class TestBaselineCLIFastPath:
    """Test fast path (simple queries)."""

    @pytest.mark.asyncio
    async def test_simple_math(self):
        """Simple math uses fast path."""
        url = config.get_url("baseline_cli")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "4" in content

    @pytest.mark.asyncio
    async def test_simple_greeting(self):
        """Simple greeting uses fast path."""
        url = config.get_url("baseline_cli")
        start_time = time.time()

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                }
            )
            elapsed = time.time() - start_time

        assert response.status_code == 200
        # Fast path should be quick (< 10s)
        assert elapsed < 10.0, f"Fast path too slow: {elapsed:.2f}s"


class TestBaselineCLIAgentPath:
    """Test agent path (complex queries)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_code_generation_uses_agent(self):
        """Code generation routes to agent."""
        url = config.get_url("baseline_cli")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Write a Python script that prints Hello World"}],
                    "stream": False,
                }
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "print" in content.lower() or "hello" in content.lower()


class TestBaselineCLIStreaming:
    """Test streaming responses."""

    @pytest.mark.asyncio
    async def test_streaming_chunks(self):
        """Streaming returns multiple chunks."""
        url = config.get_url("baseline_cli")
        chunks = []

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Count to 3"}],
                    "stream": True,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line[6:] != "[DONE]":
                        try:
                            chunks.append(json.loads(line[6:]))
                        except json.JSONDecodeError:
                            pass

        assert len(chunks) > 1  # Multiple chunks


class TestBaselineCLIDebug:
    """Test debug mode (if implemented)."""

    @pytest.mark.asyncio
    async def test_debug_endpoint_exists(self):
        """Debug stream endpoint exists."""
        url = config.get_url("baseline_cli")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            # Debug endpoint may require request_id
            response = await client.get(f"{url}/v1/debug/stream/test-123")
            # May be 200 (waiting) or 404 (not found)
            assert response.status_code in [200, 404, 408]
```

### Location: `tests/integration/test_baseline_langchain_integration.py`

```python
import pytest
import httpx
from tests.config import config

class TestBaselineLangChainHealth:
    """Test baseline LangChain health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Baseline LangChain /health returns 200."""
        url = config.get_url("baseline_langchain")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            try:
                response = await client.get(f"{url}/health")
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.skip("Baseline LangChain not running")


class TestBaselineLangChainChat:
    """Test LangChain baseline chat."""

    @pytest.mark.asyncio
    async def test_simple_chat(self):
        """Simple chat works."""
        url = config.get_url("baseline_langchain")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            try:
                response = await client.post(
                    f"{url}/v1/chat/completions",
                    json={
                        "model": "baseline",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "stream": False,
                    }
                )
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.skip("Baseline LangChain not running")
```

---

## Part 3: Memory Service Integration Tests

### Location: `tests/integration/test_memory_integration.py`

```python
import pytest
import httpx
import uuid
from tests.config import config

class TestMemoryServiceHealth:
    """Test memory service health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Memory service health check."""
        url = config.memory_service_deployed
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            try:
                response = await client.get(f"{url}/health")
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.skip("Memory service not available")


class TestMemoryExtraction:
    """Test memory extraction."""

    @pytest.fixture
    def test_user_id(self):
        return str(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_extract_memories(self, test_user_id):
        """Extract memories from conversation."""
        url = config.memory_service_deployed
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    f"{url}/memories/extract",
                    json={
                        "user_id": test_user_id,
                        "conversation": [
                            {"role": "user", "content": "My favorite color is blue"},
                            {"role": "assistant", "content": "Blue is a great color!"}
                        ]
                    }
                )
                assert response.status_code == 200
                data = response.json()
                # May or may not extract a memory depending on LLM decision
                assert "memories_saved" in data
            except httpx.ConnectError:
                pytest.skip("Memory service not available")


class TestMemoryRetrieval:
    """Test memory retrieval."""

    @pytest.mark.asyncio
    async def test_get_relevant_memories(self):
        """Get relevant memories for a prompt."""
        url = config.memory_service_deployed
        test_user_id = str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{url}/memories/relevant",
                    params={
                        "user_id": test_user_id,
                        "prompt": "What's my favorite color?"
                    }
                )
                assert response.status_code == 200
                data = response.json()
                assert "memories" in data
            except httpx.ConnectError:
                pytest.skip("Memory service not available")
```

---

## Part 4: End-to-End Flow Tests

### Location: `tests/integration/test_e2e_flows.py`

```python
import pytest
import httpx
import json
from tests.config import config

class TestFullChatFlow:
    """Test complete chat flow through all components."""

    @pytest.mark.asyncio
    async def test_gateway_to_baseline_simple(self):
        """Simple query flows: UI -> Gateway -> Baseline -> Response."""
        gateway_url = config.get_url("gateway")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "What is the capital of France?"}],
                    "stream": False,
                }
            )

            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "paris" in content.lower()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """Multi-turn conversation maintains context."""
        gateway_url = config.get_url("gateway")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            # First turn
            response1 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "My name is Alice"}],
                    "stream": False,
                }
            )
            assert response1.status_code == 200

            # Second turn - should remember name
            response2 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "user", "content": "My name is Alice"},
                        {"role": "assistant", "content": response1.json()["choices"][0]["message"]["content"]},
                        {"role": "user", "content": "What is my name?"}
                    ],
                    "stream": False,
                }
            )
            assert response2.status_code == 200
            content = response2.json()["choices"][0]["message"]["content"]
            assert "alice" in content.lower()

    @pytest.mark.asyncio
    async def test_streaming_full_flow(self):
        """Streaming works end-to-end."""
        gateway_url = config.get_url("gateway")
        content_parts = []
        done_received = False

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Say 'test' and nothing else"}],
                    "stream": True,
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            done_received = True
                        else:
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta:
                                    content_parts.append(delta["content"])
                            except json.JSONDecodeError:
                                pass

        assert done_received, "Should receive [DONE] marker"
        full_content = "".join(content_parts)
        assert len(full_content) > 0


class TestCompetitorSwitching:
    """Test switching between competitors."""

    @pytest.mark.asyncio
    async def test_switch_between_baselines(self):
        """Can switch between CLI and LangChain baselines."""
        gateway_url = config.get_url("gateway")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            # Test CLI baseline
            response1 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                }
            )
            assert response1.status_code == 200

            # Test LangChain baseline (if available)
            response2 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                }
            )
            # May succeed or fail based on availability
            assert response2.status_code in [200, 404, 503]
```

---

## Part 5: Timeout and Resilience Tests

### Location: `tests/integration/test_resilience.py`

```python
import pytest
import httpx
import asyncio
from tests.config import config

class TestTimeouts:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_gateway_enforces_timeout(self):
        """Gateway returns error if request takes too long."""
        # This would need a specially crafted request that triggers timeout
        # For now, just verify the endpoint responds within reason
        pass

    @pytest.mark.asyncio
    async def test_streaming_stays_open_long_requests(self):
        """Streaming connection stays open for long agent tasks."""
        gateway_url = config.get_url("gateway")

        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Write a short poem"}],
                    "stream": True,
                }
            ) as response:
                # Should be able to read the stream without timeout
                chunks = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line)
                        if "[DONE]" in line:
                            break

                assert len(chunks) > 0


class TestRetryBehavior:
    """Test retry and fallback behavior."""

    @pytest.mark.asyncio
    async def test_invalid_competitor_falls_back(self):
        """Invalid competitor selection returns error gracefully."""
        gateway_url = config.get_url("gateway")

        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "invalid-competitor-xyz",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                }
            )
            # Should get a proper error, not a 500
            assert response.status_code in [400, 404]
```

---

## Running Integration Tests

### Commands

```bash
# Run against local services
TEST_MODE=local pytest tests/integration/ -v --tb=short

# Run against deployed services
TEST_MODE=deployed pytest tests/integration/ -v --tb=short

# Run only fast tests (skip @pytest.mark.slow)
pytest tests/integration/ -v -m "not slow"

# Run with verbose output
pytest tests/integration/ -v --tb=long -s
```

### Pre-requisites for Local Testing

```bash
# Start all services locally
cd gateway && uvicorn janus_gateway.main:app --port 8000 &
cd baseline-agent-cli && uvicorn janus_baseline_agent_cli.main:app --port 8001 &
cd baseline-langchain && uvicorn janus_baseline_langchain.main:app --port 8002 &
cd ui && npm run dev &

# Wait for services to be ready
sleep 10

# Run tests
TEST_MODE=local pytest tests/integration/ -v
```

---

## Acceptance Criteria

- [ ] Gateway health endpoint tested
- [ ] Models endpoint returns valid data
- [ ] Non-streaming chat completions work
- [ ] Streaming chat completions work with proper SSE format
- [ ] Time to first token < 5s for simple queries
- [ ] Multimodal requests (with images) accepted
- [ ] Transcription proxy tested
- [ ] Error handling returns proper status codes
- [ ] Baseline CLI fast path tested
- [ ] Baseline CLI agent path tested
- [ ] Baseline LangChain basic functionality tested
- [ ] Memory service extraction/retrieval tested
- [ ] Full end-to-end flow verified
- [ ] Multi-turn conversations work
- [ ] Competitor switching works
- [ ] Any failing tests result in code fixes

---

## Notes

- Integration tests require running services (local or deployed)
- Set `TEST_MODE=deployed` to test against production
- Use `CHUTES_FINGERPRINT` env var for auth-required tests
- Slow tests are marked with `@pytest.mark.slow`
- Failed tests indicate bugs that must be fixed

NR_OF_TRIES: 0
