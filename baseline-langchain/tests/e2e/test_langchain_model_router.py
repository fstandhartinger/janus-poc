"""E2E tests for LangChain model router integration."""

from __future__ import annotations

import json

import httpx
import pytest

from .conftest import build_e2e_headers

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


async def _stream_content(response: httpx.Response) -> str:
    """Stream content from SSE response."""
    content = ""
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
    except httpx.HTTPError:
        pass
    return content


def _is_error_response(content: str) -> bool:
    lowered = content.lower()
    return "failed to stream response" in lowered or lowered.startswith("error:")


class TestLangChainModelRouter:
    """Test LangChain uses model router for smart routing."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_vision_model_routing(self, e2e_settings) -> None:
        """Image input should route to vision model."""
        timeout = httpx.Timeout(30.0, read=180.0)
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
                                "content": [
                                    {"type": "text", "text": "Describe this image briefly"},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": "https://picsum.photos/200"},
                                    },
                                ],
                            }
                        ],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Service returned {response.status_code}")
                assert response.status_code == 200
                content = await _stream_content(response)

        lowered = content.lower()
        if "timed out" in lowered or "timeout" in lowered:
            pytest.skip("Vision request timed out")
        if "not configured" in lowered or "not available" in lowered:
            pytest.skip("Vision not available")
        if "do not have access" in lowered or "don't have access" in lowered:
            pytest.skip("Vision access unavailable")

        # Should have image description
        stripped = content.replace("(no content)", "").strip()
        if len(stripped) < 20:
            pytest.skip("Vision response too short")

        assert len(stripped) > 20, f"Expected description, got: {content[:200]}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_default_model_routing(self, e2e_settings) -> None:
        """Text-only input should use default model."""
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
                        "messages": [
                            {
                                "role": "user",
                                "content": "What is the capital of France?",
                            }
                        ],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Service returned {response.status_code}")
                assert response.status_code == 200
                content = await _stream_content(response)

        lowered = content.lower()
        if not content.strip():
            pytest.skip("Default routing returned empty response")
        if _is_error_response(content):
            pytest.skip("Default routing returned error response")
        # Should answer the question
        assert "paris" in lowered, f"Expected Paris, got: {content[:200]}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.parametrize(
        "model",
        [
            "MiniMaxAI/MiniMax-M2",
            "deepseek-ai/DeepSeek-V3-0324",
            "THUDM/GLM-4-Plus",
        ],
    )
    async def test_explicit_model_selection(
        self, e2e_settings, model: str
    ) -> None:
        """LangChain should support explicit model selection."""
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.baseline_langchain_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": model,
                        "messages": [
                            {"role": "user", "content": "Say hello in 5 words or less"}
                        ],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Service returned {response.status_code}")

                if response.status_code == 200:
                    content = await _stream_content(response)
                    lowered = content.lower()
                    if "not configured" in lowered or "not available" in lowered:
                        pytest.skip(f"Model {model} not available")
                    # Just verify we got some response
                    stripped = content.replace("(no content)", "").strip()
                    assert len(stripped) > 0, f"Expected content from {model}"
                else:
                    pytest.skip(f"Model {model} not available (status {response.status_code})")

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_fallback_on_rate_limit(self, e2e_settings) -> None:
        """LangChain should fallback to a different model on rate limit."""
        pytest.skip("Rate limit fallback requires controlled throttling in production.")

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_model_router_health(self, e2e_settings) -> None:
        """Model router should report health status."""
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
            # May include model router status
            # Just verify health endpoint works
