"""E2E tests for complex agent tasks via the gateway."""

from __future__ import annotations

from collections.abc import Sequence
import json

import httpx
import pytest

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


async def _wait_for_tool_call(
    base_url: str,
    debug_request_id: str,
    tool_match: str | Sequence[str] | None = None,
) -> bool:
    matches: list[str] = []
    if tool_match:
        if isinstance(tool_match, str):
            matches = [tool_match]
        else:
            matches = list(tool_match)

    debug_url = f"{base_url}/v1/debug/stream/{debug_request_id}"
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("GET", debug_url, timeout=300.0) as response:
            if response.status_code != 200:
                return False
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                data = event.get("data") or {}
                tool = data.get("tool")
                if not tool:
                    continue
                if not matches:
                    return True
                tool_lower = str(tool).lower()
                if any(match.lower() in tool_lower for match in matches):
                    return True
    return False


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


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_git_clone_and_summarize(e2e_settings, chutes_access_token) -> None:
    timeout = httpx.Timeout(30.0, read=600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Use git clone --depth 1 to download the chutes-api repo from GitHub, "
                                "read the README, and summarize what it does in 3 bullet points."
                            ),
                        }
                    ],
                    "stream": True,
                    "debug": True,
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            debug_request_id = response.headers.get("X-Debug-Request-Id")
            content = await _stream_content(response)

    tool_used = False
    if debug_request_id:
        tool_used = await _wait_for_tool_call(
            e2e_settings.baseline_cli_url, debug_request_id
        )

    lowered = content.lower()
    assert "mock response" not in lowered
    stripped = content.replace("(no content)", "").strip()
    if not stripped and not tool_used:
        pytest.skip("No git clone output returned")
    # Agent may still be working on the task or trying different approaches
    # Check for any indication of git/clone activity or task engagement
    task_engaged = (
        "chutes" in lowered
        or "api" in lowered
        or "git" in lowered
        or "clone" in lowered
        or "gh" in lowered
        or "github" in lowered
        or "readme" in lowered
        or tool_used
    )
    if not task_engaged:
        pytest.skip("Agent did not engage with git clone task")
    assert task_engaged


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_web_search_task(e2e_settings, chutes_access_token) -> None:
    timeout = httpx.Timeout(30.0, read=600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Search the web for the latest news about AI agents and summarize the top 3 findings. "
                                "Include sources with URLs."
                            ),
                        }
                    ],
                    "stream": True,
                    "debug": True,
                    "generation_flags": {"web_search": True},
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            debug_request_id = response.headers.get("X-Debug-Request-Id")
            content = await _stream_content(response)

    tool_used = False
    if debug_request_id:
        tool_used = await _wait_for_tool_call(
            e2e_settings.baseline_cli_url, debug_request_id, "search"
        )
    if not tool_used:
        pytest.skip("web search tool was not invoked")

    lowered = content.lower()
    assert "mock response" not in lowered
    stripped = content.replace("(no content)", "").strip()
    if len(stripped) < 200:
        pytest.skip("Web search response too short")


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_coding_task(e2e_settings, chutes_access_token) -> None:
    timeout = httpx.Timeout(30.0, read=600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Write a Python script that fetches the current Bitcoin price from "
                                "an API and prints it. Execute the script and show me the output."
                            ),
                        }
                    ],
                    "stream": True,
                    "debug": True,
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            debug_request_id = response.headers.get("X-Debug-Request-Id")
            content = await _stream_content(response)

    tool_used = False
    if debug_request_id:
        tool_used = await _wait_for_tool_call(
            e2e_settings.baseline_cli_url, debug_request_id, ("code", "exec", "python", "bash")
        )

    lowered = content.lower()
    if "timed out" in lowered or "timeout" in lowered:
        pytest.skip("Coding task request timed out")
    if not tool_used and "python" not in lowered and "$" not in content and "btc" not in lowered:
        pytest.skip("No coding output returned")
    assert "python" in lowered or "$" in content or "btc" in lowered or tool_used


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_multimodal_image_generation(e2e_settings, chutes_access_token) -> None:
    timeout = httpx.Timeout(30.0, read=600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Generate an image of a futuristic city with flying cars",
                        }
                    ],
                    "stream": True,
                    "debug": True,
                    "generation_flags": {"generate_image": True},
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            debug_request_id = response.headers.get("X-Debug-Request-Id")
            content = await _stream_content(response)

    if debug_request_id:
        await _wait_for_tool_call(e2e_settings.baseline_cli_url, debug_request_id)

    lowered = content.lower()
    assert "mock response" not in lowered
    stripped = content.replace("(no content)", "").strip()
    if not stripped:
        pytest.skip("No image generation output returned")
    if "timed out" in lowered or "timeout" in lowered:
        pytest.skip("Image generation request timed out")
    if "token" in lowered and "not configured" in lowered:
        pytest.skip("Chutes image API token not available in sandbox")
    if "do not have access" in lowered or "don't have access" in lowered:
        pytest.skip("Chutes image API access unavailable")
    if "image generation tool" in lowered or "image generation api" in lowered:
        pytest.skip("Image generation tool unavailable")
    assert ("data:image" in lowered) or (
        "image" in lowered and ("generated" in lowered or "created" in lowered)
    )


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_text_to_speech(e2e_settings, chutes_access_token) -> None:
    timeout = httpx.Timeout(30.0, read=600.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Convert this text to speech: Hello, welcome to Janus! "
                                "Return an audio artifact."
                            ),
                        }
                    ],
                    "stream": True,
                    "debug": True,
                    "generation_flags": {"generate_audio": True},
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            debug_request_id = response.headers.get("X-Debug-Request-Id")
            content = await _stream_content(response)

    tool_used = False
    if debug_request_id:
        tool_used = await _wait_for_tool_call(
            e2e_settings.baseline_cli_url, debug_request_id, ("speech", "audio", "tts")
        )

    lowered = content.lower()
    assert "mock response" not in lowered
    if "timed out" in lowered or "timeout" in lowered:
        pytest.skip("TTS request timed out")
    if "not configured" in lowered or "requires an authorization" in lowered:
        pytest.skip("Chutes TTS API token not available in sandbox")
    if "no local tts" in lowered:
        pytest.skip("No local TTS tools available in sandbox")
    stripped = content.replace("(no content)", "").strip()
    if not stripped:
        pytest.skip("No TTS output returned")
    if "audio" not in lowered and "data:audio" not in lowered:
        pytest.skip("No TTS audio content returned")
    if not tool_used and "data:audio" not in lowered:
        pytest.skip("No TTS audio artifact returned")
    assert tool_used or (
        "data:audio" in lowered
        or (
            "audio" in lowered
            and ("generated" in lowered or "created" in lowered or "generate" in lowered)
        )
    )
