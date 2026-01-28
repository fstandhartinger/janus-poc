"""Smoke tests for baseline models routed through the gateway."""

from __future__ import annotations

import httpx
import pytest

from tests.utils import is_service_available, pre_release_headers

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio, pytest.mark.smoke_baseline]

BASELINES = ["baseline-cli-agent", "baseline-langchain"]


async def _available_models(client: httpx.AsyncClient) -> set[str] | None:
    try:
        response = await client.get("/v1/models")
        if response.status_code == 404:
            return set()
        response.raise_for_status()
    except Exception:
        return None

    payload = response.json()
    return {
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    }


async def _skip_if_unavailable(client: httpx.AsyncClient, baseline: str) -> None:
    models = await _available_models(client)
    if models is not None and baseline not in models:
        pytest.skip(f"Baseline {baseline} not listed in /v1/models")


class TestBaselineSmokeGateway:
    """Smoke tests for baselines via gateway."""

    @pytest.mark.parametrize("baseline", BASELINES)
    async def test_simple_query(self, gateway_url: str, baseline: str) -> None:
        """Simple query returns a response."""
        if not await is_service_available(gateway_url):
            pytest.skip(f"Gateway not reachable at {gateway_url}")
        async with httpx.AsyncClient(
            base_url=gateway_url,
            timeout=60,
            headers=pre_release_headers() or None,
        ) as client:
            await _skip_if_unavailable(client, baseline)
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "What is 2+2?"}],
                    "stream": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            assert "error" not in content.lower() or "sorry" not in content.lower()

    @pytest.mark.parametrize("baseline", BASELINES)
    async def test_streaming_works(self, gateway_url: str, baseline: str) -> None:
        """Streaming returns chunks."""
        if not await is_service_available(gateway_url):
            pytest.skip(f"Gateway not reachable at {gateway_url}")
        chunks: list[str] = []
        async with httpx.AsyncClient(
            base_url=gateway_url,
            timeout=60,
            headers=pre_release_headers() or None,
        ) as client:
            await _skip_if_unavailable(client, baseline)
            async with client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": baseline,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            ) as response:
                assert response.status_code == 200
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and "[DONE]" not in line:
                        chunks.append(line)

        assert len(chunks) > 0, "No streaming chunks received"
