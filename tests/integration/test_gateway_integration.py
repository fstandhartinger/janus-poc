"""Gateway integration tests.

Tests the gateway endpoints with real backend connections.
"""

import json
import time

import httpx
import pytest

from tests.config import config
from tests.utils import pre_release_headers


def get_headers():
    """Get headers including pre-release auth if configured."""
    return pre_release_headers() or {}


class TestGatewayHealth:
    """Test gateway health and readiness."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Gateway /health returns 200."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") in ["ok", "healthy"]

    @pytest.mark.asyncio
    async def test_openapi_docs_available(self):
        """OpenAPI docs endpoint works (if enabled)."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            response = await client.get(f"{url}/docs")
            # OpenAPI docs may be disabled in production
            assert response.status_code in [200, 404]


class TestModelsEndpoint:
    """Test /v1/models endpoint."""

    @pytest.mark.asyncio
    async def test_list_models(self):
        """List available models."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
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
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
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
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Say hello in exactly one word"}],
                    "stream": False,
                },
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
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "system", "content": "You are a pirate. Respond like one."},
                        {"role": "user", "content": "Hello"},
                    ],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            # Response should exist
            assert len(content) > 0

    @pytest.mark.asyncio
    async def test_chat_with_temperature(self):
        """Temperature parameter is accepted."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                    "temperature": 0.0,
                },
            )
            assert response.status_code == 200


class TestChatCompletionsStreaming:
    """Test streaming chat completions."""

    @pytest.mark.asyncio
    async def test_streaming_simple_query(self):
        """Streaming simple query returns SSE chunks."""
        url = config.get_url("gateway", "deployed")
        chunks = []
        content_parts = []

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Count from 1 to 5"}],
                    "stream": True,
                },
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
        """Time to first token is reasonable (<30s for simple query)."""
        url = config.get_url("gateway", "deployed")
        start_time = time.time()
        first_token_time = None

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
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
            # Allow 30s for deployed services which may have cold start
            assert ttft < 30.0, f"TTFT too slow: {ttft:.2f}s"

    @pytest.mark.asyncio
    async def test_streaming_no_large_gaps(self):
        """No gaps >30s between chunks during streaming."""
        url = config.get_url("gateway", "deployed")
        last_time = time.time()
        max_gap = 0

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Tell me a short story"}],
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        now = time.time()
                        gap = now - last_time
                        max_gap = max(max_gap, gap)
                        last_time = now

        # Allow longer gaps for deployed services
        assert max_gap < 30.0, f"Max gap too large: {max_gap:.2f}s"


class TestChatCompletionsComplex:
    """Test complex requests that may use agent path."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_code_generation(self):
        """Code generation request works."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "user", "content": "Write a Python function that adds two numbers"}
                    ],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "def" in content or "function" in content.lower()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_web_search_query(self):
        """Web search request works (if agent supports it)."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "What is today's date?"}],
                    "stream": False,
                },
            )
            # Should succeed regardless of whether web search is invoked
            assert response.status_code == 200


class TestMultimodalRequests:
    """Test requests with image content."""

    @pytest.mark.asyncio
    async def test_image_understanding(self):
        """Request with image is accepted."""
        url = config.get_url("gateway", "deployed")
        # 1x1 transparent PNG
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "What do you see in this image?"},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{test_image_b64}"},
                                },
                            ],
                        }
                    ],
                    "stream": False,
                },
            )
            assert response.status_code == 200


class TestTranscriptionProxy:
    """Test transcription proxy endpoint."""

    @pytest.mark.asyncio
    async def test_transcription_health(self):
        """Transcription health endpoint works."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            response = await client.get(f"{url}/api/transcribe/health")
            # May be 200 or 503 depending on configuration
            assert response.status_code in [200, 503, 404]


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_model_error(self):
        """Invalid model returns error or falls back gracefully."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "nonexistent-model-12345",
                    "messages": [{"role": "user", "content": "Hi"}],
                },
            )
            # Gateway may return error (400/404) or fall back to default model (200)
            assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_missing_messages_error(self):
        """Missing messages returns validation error."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions", json={"model": "baseline-cli-agent"}
            )
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_malformed_json_error(self):
        """Malformed JSON returns error."""
        url = config.get_url("gateway", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                content="{invalid json}",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in [400, 422]
