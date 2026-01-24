"""Streaming event helpers."""

import base64
import json
import time
from typing import Any

from pydantic import BaseModel


class ScreenshotEvent(BaseModel):
    """Screenshot streaming event."""

    type: str = "screenshot"
    data: dict[str, Any]


def format_screenshot_sse(screenshot_data: bytes, url: str, title: str) -> str:
    """Format screenshot as SSE event."""
    event = {
        "type": "screenshot",
        "data": {
            "url": url,
            "title": title,
            "image_base64": base64.b64encode(screenshot_data).decode("utf-8"),
            "timestamp": time.time(),
        },
    }
    return f"data: {json.dumps(event)}\n\n"
