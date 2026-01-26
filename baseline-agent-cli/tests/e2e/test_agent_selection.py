"""E2E tests for baseline agent selection."""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def _wait_for_agent_message(
    client: httpx.AsyncClient, base_url: str, debug_request_id: str
) -> str | None:
    debug_url = f"{base_url}/v1/debug/stream/{debug_request_id}"
    async with client.stream("GET", debug_url, timeout=60.0) as debug_response:
        assert debug_response.status_code == 200
        async for line in debug_response.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            message = event.get("message", "")
            if "Starting" in message and "agent" in message:
                return message
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize("agent", ["claude-code", "codex", "aider"])
async def test_agent_responds(agent: str, e2e_settings) -> None:
    debug_request_id = f"e2e-{uuid.uuid4().hex}"
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": "Execute the command 'echo 4' and show me the output.",
                    }
                ],
                "stream": False,
                "debug": True,
            },
            headers={
                "X-Baseline-Agent": agent,
                "X-Debug-Request-Id": debug_request_id,
            },
        )

    assert response.status_code == 200
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    assert content and "4" in content

    async with httpx.AsyncClient(timeout=300.0) as client:
        agent_message = await _wait_for_agent_message(
            client, e2e_settings.baseline_cli_url, debug_request_id
        )
    assert agent_message is not None
    assert agent in agent_message


@pytest.mark.asyncio
async def test_default_agent_is_claude_code(e2e_settings) -> None:
    debug_request_id = f"e2e-{uuid.uuid4().hex}"
    payload = {
        "model": "baseline-cli-agent",
        "messages": [
            {
                "role": "user",
                "content": "Execute the command 'echo default agent test' and show me the output.",
            }
        ],
        "stream": False,
        "debug": True,
    }
    headers = {"X-Debug-Request-Id": debug_request_id}

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 200

    async with httpx.AsyncClient(timeout=300.0) as client:
        agent_message = await _wait_for_agent_message(
            client, e2e_settings.baseline_cli_url, debug_request_id
        )

    assert agent_message is not None
    assert "claude-code" in agent_message
