"""Vision helpers for GUI tools."""

from __future__ import annotations

import os
from typing import Optional

import httpx


def analyze_screenshot(
    screenshot_base64: str,
    question: str,
    model: Optional[str] = None,
) -> str:
    """Analyze a base64 screenshot with a vision-capable model.

    Args:
        screenshot_base64: Base64 PNG data
        question: Question to ask about the screenshot
        model: Optional model override

    Returns:
        Model response string
    """
    api_key = os.environ.get("CHUTES_API_KEY")
    if not api_key:
        raise RuntimeError("CHUTES_API_KEY is not set")

    api_url = os.environ.get("CHUTES_API_URL", "https://api.chutes.ai/v1")
    resolved_model = model or os.environ.get(
        "JANUS_VISION_MODEL", "Qwen/Qwen3-VL-235B-A22B-Instruct"
    )

    if screenshot_base64.startswith("data:"):
        image_url = screenshot_base64
    else:
        image_url = f"data:image/png;base64,{screenshot_base64}"

    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ],
            }
        ],
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{api_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"]
