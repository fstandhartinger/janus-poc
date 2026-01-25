"""Video generation tool for the LangChain baseline."""

from __future__ import annotations

import base64
import time
from typing import Any

import httpx
from langchain_core.tools import tool

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.services import add_artifact, get_artifact_manager, get_request_auth_token

VIDEO_TIMEOUT = 300.0
DEFAULT_VIDEO_MIME = "video/mp4"


def _post_with_retries(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    max_retries: int,
) -> httpx.Response:
    last_exc: Exception | None = None
    attempts = max(1, max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(0.5 * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("Request failed")


@tool("video_generation")
def video_generation(prompt: str) -> str:
    """Generate a video from a text prompt using Chutes."""
    settings = get_settings()
    token = get_request_auth_token() or settings.chutes_api_key
    if not token:
        return "Video generation unavailable: missing API key."

    payload = {"prompt": prompt}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{settings.chutes_api_base.rstrip('/')}/video/generate"

    try:
        response = _post_with_retries(
            url,
            headers=headers,
            payload=payload,
            timeout=VIDEO_TIMEOUT,
            max_retries=settings.max_retries,
        )
    except Exception as exc:
        return f"Video generation failed: {exc}"

    try:
        data = response.json()
    except ValueError as exc:
        return f"Video generation failed: {exc}"

    manager = get_artifact_manager()
    video_url = None
    for key in ("url", "video_url", "video"):
        value = data.get(key)
        if isinstance(value, str) and value:
            video_url = value
            break

    if video_url:
        artifact = manager.create_remote_artifact("video.mp4", video_url, DEFAULT_VIDEO_MIME)
        add_artifact(artifact)
        return f"Video generated: {video_url}"

    b64_data = data.get("b64") or data.get("b64_json") or data.get("data")
    if isinstance(b64_data, str) and b64_data:
        try:
            content = base64.b64decode(b64_data)
        except Exception as exc:
            return f"Video generation failed: {exc}"
        artifact = manager.create_artifact("video.mp4", content, DEFAULT_VIDEO_MIME)
        add_artifact(artifact)
        return f"Video generated: {artifact.url}"

    return "Video generation failed: invalid response format."


video_generation_tool = video_generation
