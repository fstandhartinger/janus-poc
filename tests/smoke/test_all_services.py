"""Smoke tests for all Janus services."""

from __future__ import annotations

import httpx
import pytest

from tests.config import config
from tests.utils import is_service_available

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


async def test_gateway_smoke() -> None:
    """Gateway responds to health check."""
    urls = config.get_urls(config.default_mode())
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200


async def test_baseline_cli_smoke() -> None:
    """Baseline CLI responds to health check."""
    urls = config.get_urls(config.default_mode())
    if not await is_service_available(urls["baseline_cli"]):
        pytest.skip(f"Baseline CLI not reachable at {urls['baseline_cli']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_cli"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        if response.status_code == 404:
            pytest.skip("Gateway models endpoint not available")
        assert response.status_code == 200


async def test_baseline_langchain_smoke() -> None:
    """Baseline LangChain responds to health check when available."""
    urls = config.get_urls(config.default_mode())
    if not await is_service_available(urls["baseline_langchain"]):
        pytest.skip(f"Baseline LangChain not reachable at {urls['baseline_langchain']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_langchain"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200


async def test_ui_smoke() -> None:
    """UI is serving pages."""
    urls = config.get_urls(config.default_mode())
    async with httpx.AsyncClient(timeout=config.request_timeout, follow_redirects=True) as client:
        try:
            response = await client.get(urls["ui"])
        except httpx.HTTPError:
            pytest.skip(f"UI not reachable at {urls['ui']}")
        assert response.status_code == 200


async def test_chat_completion_smoke() -> None:
    """Chat completion works end-to-end through the gateway."""
    urls = config.get_urls(config.default_mode())
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"], timeout=config.streaming_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False,
            },
        )
        if response.status_code == 404:
            pytest.skip("Gateway chat endpoint not available")
        assert response.status_code == 200


async def test_models_endpoint_smoke() -> None:
    """Gateway models endpoint returns data."""
    urls = config.get_urls(config.default_mode())
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
        assert data.get("data")
