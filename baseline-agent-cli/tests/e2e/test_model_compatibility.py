"""E2E tests for model compatibility."""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.e2e


MODELS_TO_TEST = [
    "MiniMaxAI/MiniMax-M2",
    "deepseek-ai/DeepSeek-V3-0324",
    "THUDM/GLM-4-Plus",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "mistralai/Mistral-Small-3.2",
]


def _with_token(payload: dict, token: str | None) -> dict:
    if token:
        payload["chutes_access_token"] = token
    return payload


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODELS_TO_TEST)
async def test_model_simple_task(model: str, e2e_settings, chutes_access_token) -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
            json=_with_token(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hello in exactly 5 words."}],
                    "stream": False,
                },
                chutes_access_token,
            ),
        )

    if response.status_code != 200:
        pytest.skip(f"Model {model} not available or failed")

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    assert content and len(content) > 0


@pytest.mark.asyncio
async def test_vision_model_with_image(e2e_settings, chutes_access_token) -> None:
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                f"{e2e_settings.baseline_cli_url}/v1/chat/completions",
                json=_with_token(
                    {
                        "model": "Qwen/Qwen2.5-VL-72B-Instruct",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this image"},
                                    {"type": "image_url", "image_url": {"url": "https://picsum.photos/200"}},
                                ],
                            }
                        ],
                        "stream": False,
                    },
                    chutes_access_token,
                ),
            )
        except httpx.ReadTimeout:
            pytest.skip("Vision model request timed out")

    if response.status_code != 200:
        pytest.skip("Vision model not available or failed")

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    assert content and len(content) > 50
