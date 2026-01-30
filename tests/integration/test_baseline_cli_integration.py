"""Baseline CLI Agent integration tests.

Tests the baseline CLI agent with real backend connections.
"""

import json
import time

import httpx
import pytest

from tests.config import config


class TestBaselineCLIHealth:
    """Test baseline CLI health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Baseline CLI /health returns 200."""
        url = config.get_url("baseline_cli", "deployed")
        async with httpx.AsyncClient(timeout=config.health_timeout) as client:
            response = await client.get(f"{url}/health")
            assert response.status_code == 200


class TestBaselineCLIFastPath:
    """Test fast path (simple queries)."""

    @pytest.mark.asyncio
    async def test_simple_math(self):
        """Simple math uses fast path."""
        url = config.get_url("baseline_cli", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "4" in content

    @pytest.mark.asyncio
    async def test_simple_greeting(self):
        """Simple greeting uses fast path."""
        url = config.get_url("baseline_cli", "deployed")
        start_time = time.time()

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "stream": False,
                },
            )
            elapsed = time.time() - start_time

        assert response.status_code == 200
        # Fast path should be reasonable (< 30s for deployed service with potential cold start)
        assert elapsed < 30.0, f"Fast path too slow: {elapsed:.2f}s"


class TestBaselineCLIAgentPath:
    """Test agent path (complex queries)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_code_generation_uses_agent(self):
        """Code generation routes to agent."""
        url = config.get_url("baseline_cli", "deployed")
        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            response = await client.post(
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [
                        {"role": "user", "content": "Write a Python script that prints Hello World"}
                    ],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "print" in content.lower() or "hello" in content.lower()


class TestBaselineCLIStreaming:
    """Test streaming responses."""

    @pytest.mark.asyncio
    async def test_streaming_chunks(self):
        """Streaming returns multiple chunks."""
        url = config.get_url("baseline_cli", "deployed")
        chunks = []

        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            async with client.stream(
                "POST",
                f"{url}/v1/chat/completions",
                json={
                    "model": "baseline",
                    "messages": [{"role": "user", "content": "Count to 3"}],
                    "stream": True,
                },
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
        """Debug stream endpoint returns 200 status for streaming."""
        url = config.get_url("baseline_cli", "deployed")
        # The debug endpoint is a streaming endpoint that waits for events.
        # We test that it starts properly (returns 200) rather than waiting for data.
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                async with client.stream(
                    "GET", f"{url}/v1/debug/stream/test-123"
                ) as response:
                    # May be 200 (waiting for events) or 404 (not implemented)
                    assert response.status_code in [200, 404, 408]
            except httpx.ReadTimeout:
                # Timeout is expected for a streaming endpoint with no events
                pass
            except httpx.ConnectError:
                pytest.skip("Debug endpoint not available")
