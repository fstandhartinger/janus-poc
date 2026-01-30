"""Integration tests for the gateway web search endpoint."""

from __future__ import annotations

import os

import httpx
import pytest

from tests.config import config
from tests.utils import is_service_available, pre_release_headers

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _has_serper_key() -> bool:
    return bool(os.getenv("SERPER_API_KEY") or os.getenv("JANUS_SERPER_API_KEY"))


@pytest.mark.parametrize("mode", config.modes())
async def test_gateway_web_search(mode: str) -> None:
    """Gateway web search endpoint returns results when Serper is configured."""
    if not _has_serper_key():
        pytest.skip("SERPER_API_KEY not configured")

    urls = config.get_urls(mode)
    if not await is_service_available(urls["gateway"]):
        pytest.skip(f"Gateway not reachable at {urls['gateway']}")

    async with httpx.AsyncClient(
        base_url=urls["gateway"],
        timeout=config.request_timeout,
        headers=pre_release_headers() or None,
    ) as client:
        response = await client.post(
            "/api/search/web",
            json={"query": "Python 3.12 release notes", "num_results": 3},
        )
        if response.status_code == 404:
            pytest.skip("Gateway search endpoint not available")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data
        for item in data:
            assert item.get("title")
            assert item.get("url")
            assert item.get("snippet")
