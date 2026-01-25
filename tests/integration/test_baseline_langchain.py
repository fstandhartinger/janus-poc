"""Integration tests for the baseline LangChain service."""

from __future__ import annotations

import httpx
import pytest

from tests.config import config
from tests.utils import is_mock_response, is_service_available

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_langchain_health(mode: str, baseline_langchain_model: str) -> None:
    """Baseline LangChain health endpoint responds."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_langchain"]):
        pytest.skip(f"Baseline LangChain not reachable at {urls['baseline_langchain']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_langchain"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert baseline_langchain_model


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_langchain_simple_query(
    mode: str, baseline_langchain_model: str
) -> None:
    """Simple queries should return a response."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_langchain"]):
        pytest.skip(f"Baseline LangChain not reachable at {urls['baseline_langchain']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_langchain"], timeout=config.request_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": baseline_langchain_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )
        if response.status_code != 200:
            pytest.skip(f"Baseline LangChain unavailable: {response.status_code}")
        content = response.json()["choices"][0]["message"]["content"]
        if not is_mock_response(content):
            assert content
