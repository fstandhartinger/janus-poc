"""End-to-end tests for core demo use cases."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import httpx
import pytest

from tests.config import config
from tests.utils import assert_contains_any, assert_response_quality, is_mock_response, is_service_available, pre_release_headers

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio, pytest.mark.slow]


@dataclass
class StreamResult:
    content: str
    reasoning: str
    has_image: bool
    elapsed: float
    first_token_time: float | None


def _gateway_model() -> str:
    return os.getenv("TEST_GATEWAY_MODEL", "baseline-agent-cli")


def _detect_image(content: str) -> bool:
    markers = ("![", "data:image", "/artifacts", "/api/artifacts", ".png", ".jpg")
    return any(marker in content for marker in markers)


async def _stream_chat(
    base_url: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> StreamResult:
    headers = {"Content-Type": "application/json", **pre_release_headers()}
    start = time.monotonic()
    content = ""
    reasoning = ""
    has_image = False
    first_token_time: float | None = None

    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            json=payload,
            timeout=timeout_seconds,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                if first_token_time is None:
                    first_token_time = time.monotonic() - start
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = parsed.get("choices", [{}])[0].get("delta", {})
                if not isinstance(delta, dict):
                    continue
                chunk_content = delta.get("content") or ""
                if chunk_content:
                    content += chunk_content
                    if not has_image and _detect_image(chunk_content):
                        has_image = True
                reasoning_chunk = delta.get("reasoning_content") or ""
                if reasoning_chunk:
                    reasoning += reasoning_chunk

    elapsed = time.monotonic() - start
    return StreamResult(
        content=content,
        reasoning=reasoning,
        has_image=has_image or _detect_image(content),
        elapsed=elapsed,
        first_token_time=first_token_time,
    )


async def _skip_if_unavailable(
    base_url: str, label: str, *, require_chat: bool = False
) -> None:
    if not await is_service_available(base_url):
        pytest.skip(f"{label} service not available at {base_url}")
    if not require_chat:
        return
    headers = {"Content-Type": "application/json", **pre_release_headers()}
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        try:
            response = await client.get("/v1/models", timeout=10)
            if response.status_code == 404:
                pytest.skip(f"{label} chat endpoints not available at {base_url}")
        except Exception as exc:
            pytest.skip(f"{label} chat endpoints not available: {exc}")


class TestCoreDemos:
    """End-to-end tests for core demo use cases (baseline CLI)."""

    @pytest.mark.asyncio
    async def test_demo_1_simple_question_fast_path(
        self, baseline_cli_url: str, baseline_cli_model: str
    ) -> None:
        await _skip_if_unavailable(baseline_cli_url, "baseline-agent-cli")
        result = await _stream_chat(
            baseline_cli_url,
            {
                "model": baseline_cli_model,
                "messages": [
                    {"role": "user", "content": "Explain why it rains"}
                ],
                "stream": True,
            },
            timeout_seconds=30,
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert result.first_token_time is not None
        assert result.first_token_time < 2.0, (
            f"First token too slow: {result.first_token_time:.2f}s"
        )
        assert result.elapsed < 10.0, f"Total response too slow: {result.elapsed:.2f}s"
        assert_contains_any(result.content, ["water", "evapor"])
        assert len(result.reasoning) == 0, "Fast path should not include reasoning"

    @pytest.mark.asyncio
    async def test_demo_2_repo_clone_summarize(
        self, baseline_cli_url: str, baseline_cli_model: str
    ) -> None:
        await _skip_if_unavailable(baseline_cli_url, "baseline-agent-cli")
        result = await _stream_chat(
            baseline_cli_url,
            {
                "model": baseline_cli_model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Clone the https://github.com/anthropics/anthropic-cookbook "
                            "repository and give me a summary of what it contains"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(180, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert result.elapsed < 180, f"Took too long: {result.elapsed:.2f}s"
        assert len(result.reasoning) > 100, "Should have reasoning tokens from agent"
        assert_contains_any(result.content, ["anthropic", "cookbook"])
        assert_contains_any(
            result.content, ["example", "notebook", "tutorial", "guide"]
        )

    @pytest.mark.asyncio
    async def test_demo_3_web_research_report(
        self, baseline_cli_url: str, baseline_cli_model: str
    ) -> None:
        await _skip_if_unavailable(baseline_cli_url, "baseline-agent-cli")
        result = await _stream_chat(
            baseline_cli_url,
            {
                "model": baseline_cli_model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Search the web for the latest developments in quantum computing in 2026 "
                            "and write me a brief report with sources"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(120, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert result.elapsed < 90, f"Took too long: {result.elapsed:.2f}s"
        assert "quantum" in result.content.lower()
        assert (
            "http" in result.content
            or "source" in result.content.lower()
            or "[" in result.content
        )
        assert len(result.content) > 500, "Report should be substantial"

    @pytest.mark.asyncio
    async def test_demo_4_image_generation(
        self, baseline_cli_url: str, baseline_cli_model: str
    ) -> None:
        await _skip_if_unavailable(baseline_cli_url, "baseline-agent-cli")
        result = await _stream_chat(
            baseline_cli_url,
            {
                "model": baseline_cli_model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Generate an image of a futuristic city with flying cars at sunset"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(60, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert result.elapsed < 45, f"Took too long: {result.elapsed:.2f}s"
        assert result.has_image, "Response should contain an image"


class TestCoreDemosViaGateway:
    """Core demos through the gateway (full stack)."""

    @pytest.mark.asyncio
    async def test_gateway_demo_1_simple(self, gateway_url: str) -> None:
        await _skip_if_unavailable(gateway_url, "gateway", require_chat=True)
        result = await _stream_chat(
            gateway_url,
            {
                "model": _gateway_model(),
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "stream": True,
            },
            timeout_seconds=30,
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert "4" in result.content

    @pytest.mark.asyncio
    async def test_gateway_demo_2_repo_clone(self, gateway_url: str) -> None:
        await _skip_if_unavailable(gateway_url, "gateway", require_chat=True)
        result = await _stream_chat(
            gateway_url,
            {
                "model": _gateway_model(),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Clone the https://github.com/anthropics/anthropic-cookbook "
                            "repository and give me a summary of what it contains"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(180, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert_contains_any(result.content, ["anthropic", "cookbook"])

    @pytest.mark.asyncio
    async def test_gateway_demo_3_research(self, gateway_url: str) -> None:
        await _skip_if_unavailable(gateway_url, "gateway", require_chat=True)
        result = await _stream_chat(
            gateway_url,
            {
                "model": _gateway_model(),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Search the web for the latest developments in quantum computing in 2026 "
                            "and write me a brief report with sources"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(120, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert "quantum" in result.content.lower()
        assert (
            "http" in result.content
            or "source" in result.content.lower()
            or "[" in result.content
        )

    @pytest.mark.asyncio
    async def test_gateway_demo_4_image(self, gateway_url: str) -> None:
        await _skip_if_unavailable(gateway_url, "gateway", require_chat=True)
        result = await _stream_chat(
            gateway_url,
            {
                "model": _gateway_model(),
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Generate an image of a futuristic city with flying cars at sunset"
                        ),
                    }
                ],
                "stream": True,
            },
            timeout_seconds=max(60, config.streaming_timeout),
        )

        if is_mock_response(result.content):
            assert_response_quality(result.content)
            return

        assert result.has_image, "Response should contain an image"
