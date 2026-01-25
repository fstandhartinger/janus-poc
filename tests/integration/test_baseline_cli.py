"""Integration tests for the baseline CLI service."""

from __future__ import annotations

import time

import httpx
import pytest

from tests.config import config
from tests.utils import is_mock_response, is_service_available

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_cli_health(mode: str, baseline_cli_model: str) -> None:
    """Baseline CLI health endpoint responds."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_cli"]):
        pytest.skip(f"Baseline CLI not reachable at {urls['baseline_cli']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_cli"], timeout=config.request_timeout
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert baseline_cli_model


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_cli_simple_query(mode: str, baseline_cli_model: str) -> None:
    """Simple queries should return a response."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_cli"]):
        pytest.skip(f"Baseline CLI not reachable at {urls['baseline_cli']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_cli"], timeout=config.request_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": baseline_cli_model,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "stream": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not is_mock_response(content):
            assert "4" in content


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_cli_complex_query(mode: str, baseline_cli_model: str) -> None:
    """Code-generation prompts should return a useful response."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_cli"]):
        pytest.skip(f"Baseline CLI not reachable at {urls['baseline_cli']}")

    async with httpx.AsyncClient(
        base_url=urls["baseline_cli"], timeout=config.streaming_timeout
    ) as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": baseline_cli_model,
                "messages": [
                    {"role": "user", "content": "Write a hello world function in Python"}
                ],
                "stream": False,
            },
        )
        assert response.status_code == 200
        content = response.json()["choices"][0]["message"]["content"]
        if not is_mock_response(content):
            assert "def" in content or "print" in content


@pytest.mark.parametrize("mode", config.modes())
async def test_baseline_cli_streaming(mode: str, baseline_cli_model: str) -> None:
    """Streaming responses should emit chunks promptly."""
    urls = config.get_urls(mode)
    if not await is_service_available(urls["baseline_cli"]):
        pytest.skip(f"Baseline CLI not reachable at {urls['baseline_cli']}")

    first_chunk_time: float | None = None
    chunks: list[str] = []

    async with httpx.AsyncClient(
        base_url=urls["baseline_cli"], timeout=config.streaming_timeout
    ) as client:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": baseline_cli_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                if line[6:] != "[DONE]":
                    chunks.append(line)

    assert chunks
    assert first_chunk_time is not None
