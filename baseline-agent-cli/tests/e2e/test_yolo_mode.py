"""E2E tests for yolo/bypass permission mode."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.e2e


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_file_operations_no_prompt(e2e_settings, chutes_access_token) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
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
                    "stream": False,
                },
                chutes_access_token,
            ),
        )

    assert response.status_code == 200
    data = response.json()
    content = data["choices"][0]["message"]["content"]

    assert "hello world" in content.lower() or "created" in content.lower()
    assert "permission" not in content.lower() or "granted" in content.lower()


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_command_execution_no_prompt(e2e_settings, chutes_access_token) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
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
                    "stream": False,
                },
                chutes_access_token,
            ),
        )

    assert response.status_code == 200
    data = response.json()
    content = data["choices"][0]["message"]["content"]

    assert "Hello from the sandbox" in content
