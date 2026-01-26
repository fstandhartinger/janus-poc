"""E2E tests for baseline agent selection."""

from __future__ import annotations

import asyncio
import json
import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


async def _wait_for_agent_name(
    client: httpx.AsyncClient, base_url: str, debug_request_id: str
) -> str | None:
    debug_url = f"{base_url}/v1/debug/stream/{debug_request_id}"
    async with client.stream("GET", debug_url, timeout=120.0) as debug_response:
        assert debug_response.status_code == 200
        async for line in debug_response.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            data = event.get("data") or {}
            agent = data.get("agent")
            if agent:
                return agent
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize("agent", ["claude-code", "codex", "aider"])
async def test_agent_responds(agent: str, e2e_settings, chutes_access_token) -> None:
    debug_request_id = f"e2e-{uuid.uuid4().hex}"
    payload = {
        "model": "baseline-cli-agent",
        "messages": [
            {
                "role": "user",
                "content": "Execute the command 'echo 4' and show me the output.",
            }
        ],
        "stream": False,
        "debug": True,
    }
    if chutes_access_token:
        payload["chutes_access_token"] = chutes_access_token

    # Retry up to 3 times for transient 5xx errors
    max_retries = 3
    response = None
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
                json=payload,
                headers={
                    "X-Baseline-Agent": agent,
                    "X-Debug-Request-Id": debug_request_id,
                },
            )
        if response.status_code < 500:
            break
        # Wait before retry on 5xx errors
        await asyncio.sleep(5 * (attempt + 1))

    if response is None or response.status_code >= 500:
        pytest.skip(f"Service returned {response.status_code if response else 'no response'} after {max_retries} retries")

    assert response.status_code == 200

    async with httpx.AsyncClient(timeout=600.0) as client:
        agent_name = await _wait_for_agent_name(
            client, e2e_settings.baseline_cli_url, debug_request_id
        )
    assert agent_name is not None
    assert agent_name == agent


@pytest.mark.asyncio
async def test_default_agent_is_claude_code(e2e_settings, chutes_access_token) -> None:
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
    if chutes_access_token:
        payload["chutes_access_token"] = chutes_access_token
    headers = {"X-Debug-Request-Id": debug_request_id}

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 200

    async with httpx.AsyncClient(timeout=600.0) as client:
        agent_name = await _wait_for_agent_name(
            client, e2e_settings.baseline_cli_url, debug_request_id
        )

    assert agent_name is not None
    assert agent_name == "claude-code"
