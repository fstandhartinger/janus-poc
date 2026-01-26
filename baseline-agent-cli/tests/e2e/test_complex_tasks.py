"""E2E tests for complex agent tasks via the gateway."""

from __future__ import annotations

import json

import httpx
import pytest

pytestmark = pytest.mark.e2e


def _extract_message(data: dict) -> dict:
    choices = data.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message")
    if isinstance(message, dict):
        return message
    return {}


def _extract_artifacts(data: dict) -> list[dict]:
    artifacts = data.get("artifacts")
    if artifacts:
        return artifacts
    message = _extract_message(data)
    return message.get("artifacts") or []


@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_git_clone_and_summarize(e2e_settings) -> None:
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=700.0)) as client:
        async with client.stream(
            "POST",
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Use git clone to download the chutes-api repo from GitHub, read the "
                            "README, and summarize what it does in 3 bullet points."
                        ),
                    }
                ],
                "stream": True,
            },
        ) as response:
            assert response.status_code == 200
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
                delta = choices[0].get("delta", {})
                content += delta.get("content", "")

    assert "chutes" in content.lower() or "api" in content.lower()
    assert "llm.chutes.ai/v1/chat/completions" not in content


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_web_search_task(e2e_settings) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": "Search the web for the latest news about AI agents and summarize the top 3 findings",
                    }
                ],
                "stream": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    content = _extract_message(data).get("content", "")

    assert len(content) > 200
    assert any(word in content.lower() for word in ["source", "found", "according", "report"])


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_coding_task(e2e_settings) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json={
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
                "stream": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    content = _extract_message(data).get("content", "")

    assert "python" in content.lower() or "$" in content or "btc" in content.lower()


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_multimodal_image_generation(e2e_settings) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": "Generate an image of a futuristic city with flying cars",
                    }
                ],
                "stream": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    artifacts = _extract_artifacts(data)
    has_image = any(
        artifact.get("type") == "image"
        or "image" in str(artifact.get("mime_type", "")).lower()
        for artifact in artifacts
    )
    content = _extract_message(data).get("content", "")
    assert has_image or "generated" in content.lower()


@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_text_to_speech(e2e_settings) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{e2e_settings.gateway_url}/v1/chat/completions",
            json={
                "model": "baseline-cli-agent",
                "messages": [
                    {
                        "role": "user",
                        "content": "Convert this text to speech: Hello, welcome to Janus!",
                    }
                ],
                "stream": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    artifacts = _extract_artifacts(data)
    has_audio = any(
        artifact.get("type") == "audio"
        or "audio" in str(artifact.get("mime_type", "")).lower()
        for artifact in artifacts
    )
    content = _extract_message(data).get("content", "")
    assert has_audio or "audio" in content.lower()
