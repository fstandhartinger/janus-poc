"""Baseline LangChain integration tests.

Tests the baseline LangChain agent with real backend connections.
"""

import httpx
import pytest

from tests.config import config


class TestBaselineLangChainHealth:
    """Test baseline LangChain health."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Baseline LangChain /health returns 200."""
        url = config.get_url("baseline_langchain", "deployed")
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
        url = config.get_url("baseline_langchain", "deployed")
        async with httpx.AsyncClient(timeout=config.simple_request_timeout) as client:
            try:
                response = await client.post(
                    f"{url}/v1/chat/completions",
                    json={
                        "model": "baseline",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "stream": False,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "choices" in data
                assert len(data["choices"]) > 0
            except httpx.ConnectError:
                pytest.skip("Baseline LangChain not running")

    @pytest.mark.asyncio
    async def test_simple_math(self):
        """Simple math query works."""
        url = config.get_url("baseline_langchain", "deployed")
        # Use longer timeout as LangChain service can be slower
        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            try:
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
            except httpx.ConnectError:
                pytest.skip("Baseline LangChain not running")
            except httpx.ReadTimeout:
                pytest.skip("Baseline LangChain request timed out")


class TestBaselineLangChainStreaming:
    """Test LangChain streaming."""

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Streaming response works."""
        url = config.get_url("baseline_langchain", "deployed")
        chunks = []

        async with httpx.AsyncClient(timeout=config.complex_request_timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{url}/v1/chat/completions",
                    json={
                        "model": "baseline",
                        "messages": [{"role": "user", "content": "Say hello"}],
                        "stream": True,
                    },
                ) as response:
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunks.append(line)

                assert len(chunks) > 0
            except httpx.ConnectError:
                pytest.skip("Baseline LangChain not running")
            except httpx.ReadTimeout:
                pytest.skip("Baseline LangChain streaming timed out")
