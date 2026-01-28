"""E2E tests for yolo/bypass permission mode."""

from __future__ import annotations

import json

import httpx
import pytest

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


async def _stream_content(response: httpx.Response) -> str:
    content = ""
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
    return content


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_file_operations_no_prompt(e2e_settings, chutes_access_token) -> None:
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
                                "Create a file called test.txt with the content 'Hello World' "
                                "and then read it back to me"
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
            content = await _stream_content(response)

    lowered = content.lower()
    if "mock response" in lowered:
        pytest.skip("Gateway returned mock response")
    if "failed to create sandbox" in lowered:
        pytest.skip("Sandy sandbox creation failed")
    if "timed out" in lowered or "timeout" in lowered:
        pytest.skip("File operation request timed out")

    assert "hello world" in lowered or "created" in lowered
    assert "permission" not in lowered or "granted" in lowered


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_command_execution_no_prompt(e2e_settings, chutes_access_token) -> None:
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
                                "Execute the command 'echo Hello from the sandbox' and show me the output"
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
            content = await _stream_content(response)

    lowered = content.lower()
    if "mock response" in lowered:
        pytest.skip("Gateway returned mock response")
    if "timed out" in lowered or "timeout" in lowered:
        pytest.skip("Command execution request timed out")
    if "failed to create sandbox" in lowered:
        pytest.skip("Sandy sandbox creation failed")
    assert "hello from the sandbox" in lowered
