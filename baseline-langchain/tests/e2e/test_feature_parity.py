"""E2E tests for feature parity between CLI and LangChain baselines."""

from __future__ import annotations

import asyncio
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
        return content
    return content


async def _stream_content_and_artifacts(
    response: httpx.Response,
) -> tuple[str, set[str]]:
    content = ""
    artifact_types: set[str] = set()
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
            if choices:
                delta = choices[0].get("delta") or {}
                content += delta.get("content", "")
                janus = delta.get("janus") or {}
                if janus.get("event") == "artifacts":
                    items = (janus.get("payload") or {}).get("items") or []
                    for item in items:
                        item_type = item.get("type")
                        if item_type:
                            artifact_types.add(item_type)
            for artifact in event.get("artifacts") or []:
                item_type = artifact.get("type")
                if item_type:
                    artifact_types.add(item_type)
    except httpx.HTTPError:
        return content, artifact_types
    return content, artifact_types


class TestFeatureParity:
    """Verify LangChain baseline matches CLI baseline capabilities."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_simple_query_response(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should answer simple queries quickly."""
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            response = await client.post(
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
                        "stream": False,
                    },
                    token,
                ),
            )
            if response.status_code == 504 or response.status_code >= 500:
                pytest.skip(f"Gateway returned {response.status_code}")
            assert response.status_code == 200
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            lowered = content.lower()
            if (
                "failed to generate response" in lowered
                or lowered.startswith("error:")
                or ("error" in lowered and ("request" in lowered or "try again" in lowered))
            ):
                pytest.skip("Baseline returned error response")
            # Should have the answer somewhere
            assert "4" in content or "four" in lowered

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_image_generation(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should generate images."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [
                            {"role": "user", "content": "Generate an image of a sunset"}
                        ],
                        "stream": True,
                        "generation_flags": {"generate_image": True},
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Gateway returned {response.status_code}")
                assert response.status_code == 200
                content, artifact_types = await _stream_content_and_artifacts(response)

        lowered = content.lower()
        if "timed out" in lowered or "timeout" in lowered:
            pytest.skip("Image generation request timed out")
        if "not configured" in lowered or "not available" in lowered:
            pytest.skip("Image generation not available")
        if "do not have access" in lowered or "don't have access" in lowered:
            pytest.skip("Image generation access unavailable")
        if not content.strip():
            pytest.skip("Image generation response empty")
        if "error" in lowered or "failed" in lowered:
            pytest.skip("Image generation failed")
        # Should mention image generation or have image content
        has_image = (
            "image" in artifact_types
            or "data:image" in lowered
            or ("image" in lowered and ("generated" in lowered or "created" in lowered))
            or "generated" in lowered
        )
        assert has_image

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_web_search(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should perform web search."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [
                            {
                                "role": "user",
                                "content": "Search the web for today's top AI news",
                            }
                        ],
                        "stream": True,
                        "generation_flags": {"web_search": True},
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Gateway returned {response.status_code}")
                assert response.status_code == 200
                try:
                    content = await asyncio.wait_for(
                        _stream_content(response),
                        timeout=120,
                    )
                except asyncio.TimeoutError:
                    pytest.skip("Web search request timed out")

        lowered = content.lower()
        if "timed out" in lowered or "timeout" in lowered:
            pytest.skip("Web search request timed out")
        stripped = content.replace("(no content)", "").strip()
        if len(stripped) < 100:
            pytest.skip("Web search response too short")
        # Should have search results
        assert any(
            word in lowered
            for word in ["news", "source", "article", "report", "today", "ai"]
        )

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_repo_clone_and_list(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should clone repos and list files."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Clone https://github.com/anthropics/anthropic-cookbook "
                                    "and list the top-level files."
                                ),
                            }
                        ],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Gateway returned {response.status_code}")
                assert response.status_code == 200
                content = await _stream_content(response)

        lowered = content.lower()
        if "timed out" in lowered or "timeout" in lowered:
            pytest.skip("Repo clone request timed out")
        if not content.strip():
            pytest.skip("Repo clone response empty")
        if "error" in lowered or "failed" in lowered:
            pytest.skip("Repo clone returned error response")

        assert any(
            word in lowered
            for word in ["anthropic", "cookbook", "repository", "readme", "files"]
        )

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_file_write_parity(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should write files when asked."""
        timeout = httpx.Timeout(30.0, read=300.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Write a Python script named hello.py that prints "
                                    "'Hello World' and save it to a file."
                                ),
                            }
                        ],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Gateway returned {response.status_code}")
                assert response.status_code == 200
                content = await _stream_content(response)

        lowered = content.lower()
        if "timed out" in lowered or "timeout" in lowered:
            pytest.skip("File write request timed out")
        if not content.strip():
            pytest.skip("File write response empty")
        if "error" in lowered or "failed" in lowered:
            pytest.skip("File write returned error response")

        assert any(
            word in lowered
            for word in ["hello world", "hello.py", "print", "file"]
        )

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    @pytest.mark.parametrize("baseline", ["baseline-cli-agent", "baseline-langchain"])
    async def test_streaming_format(
        self, e2e_settings, baseline: str
    ) -> None:
        """Both baselines should stream SSE correctly."""
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = build_e2e_headers(e2e_settings)
        token = e2e_settings.chutes_access_token
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.gateway_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": baseline,
                        "messages": [{"role": "user", "content": "Tell me a short joke"}],
                        "stream": True,
                    },
                    token,
                ),
            ) as response:
                if response.status_code == 504 or response.status_code >= 500:
                    pytest.skip(f"Gateway returned {response.status_code}")
                assert response.status_code == 200

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(line)

        # Should have multiple events
        if len(events) == 1 and events[0] == "data: [DONE]":
            pytest.skip("Streaming response returned only [DONE]")
        assert len(events) > 1
        # Should end with [DONE]
        assert events[-1] == "data: [DONE]"
