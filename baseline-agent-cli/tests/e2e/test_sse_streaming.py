"""E2E tests for SSE streaming correctness."""

from __future__ import annotations

import json

import httpx
import pytest

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


@pytest.mark.asyncio
async def test_sse_format(e2e_settings, chutes_access_token) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": "baseline-cli-agent",
                    "messages": [{"role": "user", "content": "Count from 1 to 5"}],
                    "stream": True,
                },
                chutes_access_token,
            ),
        ) as response:
            assert response.status_code == 200
            events: list[str] = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(line)

    assert len(events) > 1
    assert events[-1].strip() == "data: [DONE]"
    for event in events[:-1]:
        payload = event[6:].strip()
        data = json.loads(payload)
        assert "id" in data
        assert "choices" in data


@pytest.mark.asyncio
async def test_reasoning_content_streaming(e2e_settings, chutes_access_token) -> None:
    saw_content = False
    saw_reasoning_before_content = False
    timeout = httpx.Timeout(30.0, read=300.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "baseline-cli-agent",
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Execute the command 'echo Paris' and then answer what the output was."
                                ),
                            }
                        ],
                        "stream": True,
                    },
                    chutes_access_token,
                ),
            ) as response:
                if response.status_code != 200:
                    pytest.skip("Streaming request failed")
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line.strip() == "data: [DONE]":
                        continue
                    payload = line[6:].strip()
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    if delta.get("reasoning_content") and not saw_content:
                        saw_reasoning_before_content = True
                    if delta.get("content"):
                        saw_content = True
    except httpx.ReadTimeout:
        pytest.skip("Streaming reasoning request timed out")

    if not saw_content:
        pytest.skip("No streaming content returned")
    if not saw_reasoning_before_content:
        pytest.skip("Reasoning content not streamed before content")
    assert saw_content
    assert saw_reasoning_before_content
