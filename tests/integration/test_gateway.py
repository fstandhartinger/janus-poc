"""Integration tests for the Janus Gateway."""

from __future__ import annotations

import json

import httpx
import pytest

from tests.config import config
from tests.utils import is_service_available

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_health(mode: str) -> None:
    """Gateway health endpoint responds."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_chat_completion(mode: str) -> None:
    """Gateway responds to a simple chat completion."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.request_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": False,
            },
        )
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert data["choices"]


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_streaming_chat(mode: str) -> None:
    """Gateway streams chat completions."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    chunks: list[dict] = []
    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.streaming_timeout
    ) as client:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "Count to 5"}],
                "stream": True,
            },
        ) as response:
            if response.status_code == 404:
                pytest.skip("Gateway chat endpoint not available")
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                chunks.append(json.loads(payload))

    assert chunks
    for chunk in chunks:
        assert "id" in chunk
        assert "choices" in chunk


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_multimodal_request(mode: str) -> None:
    """Gateway handles multimodal inputs."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    test_image_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
        "WjR9awAAAABJRU5ErkJggg=="
    )

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.streaming_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What color is this?"},
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
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_models_endpoint(mode: str) -> None:
    """Gateway models endpoint returns models."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/v1/models")
        if response.status_code == 404:
            pytest.skip("Gateway models endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        models = [item.get("id") for item in data["data"]]
        assert any(model for model in models)


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_transcription_health(mode: str) -> None:
    """Gateway transcription health endpoint responds."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/api/transcribe/health")
        if response.status_code == 404:
            pytest.skip("Gateway transcription endpoint not available")
        assert response.status_code == 200
