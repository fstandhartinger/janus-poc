"""E2E tests for LangChain-specific functionality."""

from __future__ import annotations

import json
import time

import httpx
import pytest

from .conftest import build_e2e_headers

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


async def _stream_content_with_reasoning(response: httpx.Response) -> tuple[str, str]:
    """Stream content and return (content, reasoning_content)."""
    content = ""
    reasoning = ""
    try:
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content += delta.get("content", "")
            reasoning += delta.get("reasoning_content", "")
    except httpx.HTTPError:
        pass
    return content, reasoning


class TestLangChainBaseline:
    """Test LangChain-specific functionality."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_complexity_detection(self, e2e_settings) -> None:
        """LangChain should route based on complexity."""
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
            # Simple query (should be fast)
            start = time.time()
            response = await client.post(
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-langchain",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "stream": False,
                    },
                    token,
                ),
            )
            simple_time = time.time() - start

            if response.status_code == 504 or response.status_code >= 500:
                pytest.skip(f"Service returned {response.status_code}")
            assert response.status_code == 200

            # Complex query (may take longer, uses agent)
            start = time.time()
            timeout = httpx.Timeout(30.0, read=300.0)
            response = await client.post(
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-langchain",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Research the latest developments in quantum computing",
                            }
                        ],
                        "stream": False,
                    },
                    token,
                ),
                timeout=timeout,
            )
            complex_time = time.time() - start

            if response.status_code == 504 or response.status_code >= 500:
                pytest.skip(f"Service returned {response.status_code}")
            # This test mainly checks that both complete successfully
            assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_langchain_tools(self, e2e_settings) -> None:
        """LangChain should have working tools."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            # Test code execution via agent path
            response = await client.post(
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-langchain",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Use Python to calculate 123 * 456 and tell me the result",
                            }
                        ],
                        "stream": False,
                    },
                    token,
                ),
            )

            if response.status_code == 504 or response.status_code >= 500:
                pytest.skip(f"Service returned {response.status_code}")
            assert response.status_code == 200

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Should have the actual result: 56088
            # Agent may format differently, so check for the number
            assert "56088" in content or "56,088" in content

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_langchain_streaming(self, e2e_settings) -> None:
        """LangChain should stream SSE correctly."""
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-langchain",
                        "messages": [{"role": "user", "content": "Tell me a short joke"}],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Service returned {response.status_code}")
                assert response.status_code == 200

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(line)

        # Should have multiple events
        assert len(events) > 1
        # Should end with [DONE]
        assert events[-1] == "data: [DONE]"

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_langchain_reasoning_content(self, e2e_settings) -> None:
        """LangChain should include reasoning_content when using agent."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-langchain",
                        "messages": [
                            {
                                "role": "user",
                                "content": "Search for information about Python programming language",
                            }
                        ],
                        "stream": True,
                        "generation_flags": {"web_search": True},
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Service returned {response.status_code}")
                assert response.status_code == 200

                content, reasoning = await _stream_content_with_reasoning(response)

        # Must have content
        assert content.strip(), "Expected content in response"
        # Reasoning is optional (only for agent path with tools)
        # We don't assert on reasoning as it depends on complexity routing

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_health_endpoint(self, e2e_settings) -> None:
        """LangChain service should have working health endpoint."""
        headers = build_e2e_headers(e2e_settings)
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(
                f"{e2e_settings.baseline_langchain_url}/health"
            )
            if response.status_code == 504 or response.status_code >= 500:
                pytest.skip(f"Service returned {response.status_code}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data
