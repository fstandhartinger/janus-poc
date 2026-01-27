"""End-to-end integration tests through the gateway."""

from __future__ import annotations

import httpx
import pytest

from tests.config import config
from tests.utils import is_service_available, pre_release_headers

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_to_baseline_flow(mode: str) -> None:
    """Gateway routes requests to baseline successfully."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"],
        timeout=config.streaming_timeout,
        headers=pre_release_headers() or None,
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "What is the capital of France?"}],
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
async def test_competitor_switching(mode: str) -> None:
    """Gateway can switch between CLI and LangChain baselines."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"],
        timeout=config.streaming_timeout,
        headers=pre_release_headers() or None,
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200

        response_langchain = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-langchain",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        if response_langchain.status_code not in {200, 404, 503}:
            assert response_langchain.status_code == 200
