"""Tests for screenshot SSE formatting."""

import base64
import json

from janus_gateway.models.streaming import format_screenshot_sse


def test_format_screenshot_sse() -> None:
    payload = format_screenshot_sse(b"png-bytes", "https://example.com", "Example")
    assert payload.startswith("data: ")
    assert payload.endswith("\n\n")

    data = json.loads(payload[5:].strip())
    assert data["type"] == "screenshot"
    assert data["data"]["url"] == "https://example.com"
    assert data["data"]["title"] == "Example"
    assert data["data"]["image_base64"] == base64.b64encode(b"png-bytes").decode("utf-8")
