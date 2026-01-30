"""End-to-end flow integration tests.

Tests complete flows through all components.
"""

import json

import httpx
import pytest

from tests.config import config
from tests.utils import pre_release_headers


def get_headers():
    """Get headers including pre-release auth if configured."""
    return pre_release_headers() or {}


class TestFullChatFlow:
    """Test complete chat flow through all components."""

    @pytest.mark.asyncio
    async def test_gateway_to_baseline_simple(self):
        """Simple query flows: UI -> Gateway -> Baseline -> Response."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "user", "content": "What is the capital of France?"}
                    ],
                    "stream": False,
                },
            )

            assert response.status_code == 200
            content = response.json()["choices"][0]["message"]["content"]
            assert "paris" in content.lower()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """Multi-turn conversation maintains context."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            # First turn
            response1 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "My name is Alice"}],
                    "stream": False,
                },
            )
            assert response1.status_code == 200

            # Second turn - should remember name
            response2 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "user", "content": "My name is Alice"},
                        {
                            "role": "assistant",
                            "content": response1.json()["choices"][0]["message"]["content"],
                        },
                        {"role": "user", "content": "What is my name?"},
                    ],
                    "stream": False,
                },
            )
            assert response2.status_code == 200
            content = response2.json()["choices"][0]["message"]["content"]
            assert "alice" in content.lower()

    @pytest.mark.asyncio
    async def test_streaming_full_flow(self):
        """Streaming works end-to-end."""
        gateway_url = config.get_url("gateway", "deployed")
        content_parts = []
        done_received = False

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [
                        {"role": "user", "content": "Say 'test' and nothing else"}
                    ],
                    "stream": True,
                },
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
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            # Test CLI baseline
            response1 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )
            assert response1.status_code == 200

            # Test LangChain baseline (if available)
            response2 = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-langchain",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )
            # May succeed or fail based on availability
            assert response2.status_code in [200, 404, 503]


class TestErrorPropagation:
    """Test error propagation through the stack."""

    @pytest.mark.asyncio
    async def test_invalid_model_error_from_gateway(self):
        """Gateway handles invalid model gracefully."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "completely-invalid-model",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )
            # Gateway may return error (400/404) or fall back to default model (200)
            assert response.status_code in [200, 400, 404]
            # If error, should have error message; if 200, should have choices
            data = response.json()
            if response.status_code in [400, 404]:
                assert "error" in data or "detail" in data
            else:
                assert "choices" in data


class TestResponseStructure:
    """Test response structure compliance."""

    @pytest.mark.asyncio
    async def test_chat_completion_structure(self):
        """Chat completion response has all required fields."""
        gateway_url = config.get_url("gateway", "deployed")

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            response = await client.post(
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()

            # OpenAI-compatible structure
            assert "id" in data
            assert "object" in data
            assert data["object"] == "chat.completion"
            assert "created" in data
            assert "model" in data
            assert "choices" in data
            assert isinstance(data["choices"], list)
            assert len(data["choices"]) > 0

            choice = data["choices"][0]
            assert "index" in choice
            assert "message" in choice
            assert "role" in choice["message"]
            assert "content" in choice["message"]
            assert choice["message"]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_streaming_chunk_structure(self):
        """Streaming chunks have correct structure."""
        gateway_url = config.get_url("gateway", "deployed")
        first_chunk = None

        async with httpx.AsyncClient(timeout=config.simple_request_timeout, headers=get_headers()) as client:
            async with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                json={
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line[6:] != "[DONE]":
                        try:
                            first_chunk = json.loads(line[6:])
                            break
                        except json.JSONDecodeError:
                            pass

        assert first_chunk is not None
        assert "id" in first_chunk
        assert "object" in first_chunk
        assert first_chunk["object"] == "chat.completion.chunk"
        assert "choices" in first_chunk
