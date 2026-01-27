"""Helpers for baseline smoke tests."""

from __future__ import annotations

import ast
import os
import re
from typing import Iterable

import httpx

PRE_RELEASE_HEADER = "X-PreReleasePassword"


def pre_release_headers() -> dict[str, str]:
    """Return pre-release headers when password is configured."""
    password = os.getenv("CHUTES_JANUS_PRE_RELEASE_PWD")
    if not password:
        return {}
    return {PRE_RELEASE_HEADER: password}


async def create_test_client(base_url: str) -> httpx.AsyncClient:
    """Create configured test client."""
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=60.0,
        headers={"Content-Type": "application/json", **pre_release_headers()},
    )


async def is_service_available(base_url: str, timeout: float = 2.0) -> bool:
    """Check if a baseline service is reachable."""
    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers=pre_release_headers() or None,
        ) as client:
            response = await client.get("/health")
            response.raise_for_status()
        return True
    except Exception:
        return False


def is_mock_response(response: str) -> bool:
    """Detect mock responses from baseline services."""
    lowered = response.lower()
    return "mock mode" in lowered or "baseline is running" in lowered


def assert_response_quality(response: str, min_coherence: float = 0.7) -> None:
    """Assert response meets baseline quality threshold."""
    assert response, "Response is empty"
    if is_mock_response(response):
        assert len(response) > 10
        return
    assert len(response) > 10, "Response too short"
    assert not response.startswith("Error"), "Response is an error"
    _ = min_coherence  # Placeholder for optional scoring.


def assert_contains_any(response: str, keywords: Iterable[str]) -> None:
    """Assert response contains at least one keyword or is mock."""
    if is_mock_response(response):
        assert_response_quality(response)
        return
    lowered = response.lower()
    assert any(keyword.lower() in lowered for keyword in keywords)


def extract_code_blocks(text: str) -> list[str]:
    """Extract code blocks from markdown text."""
    pattern = r"```(?:\w+)?\n(.*?)```"
    return re.findall(pattern, text, re.DOTALL)


def assert_valid_python(code_blocks: list[str]) -> None:
    """Assert code blocks are valid Python syntax."""
    for code in code_blocks:
        if not code.strip():
            continue
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise AssertionError(f"Invalid Python syntax: {exc}")


def resolve_default_model(default: str) -> str:
    """Resolve model name from environment, falling back to default."""
    return os.getenv("BASELINE_SMOKE_MODEL", default)


def _format_message_content(content: str, images: list[str] | None) -> object:
    if not images:
        return content
    return [
        {"type": "text", "text": content},
        *[{"type": "image_url", "image_url": {"url": url}} for url in images],
    ]


async def send_message(
    client: httpx.AsyncClient,
    content: str,
    images: list[str] | None = None,
    timeout: float = 30.0,
    model: str | None = None,
) -> str:
    """Send a chat message and return response."""
    messages = [{"role": "user", "content": _format_message_content(content, images)}]
    resolved_model = model or getattr(client, "_janus_model", None)
    if resolved_model is None:
        resolved_model = resolve_default_model("baseline")

    response = await client.post(
        "/v1/chat/completions",
        json={"model": resolved_model, "messages": messages},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
