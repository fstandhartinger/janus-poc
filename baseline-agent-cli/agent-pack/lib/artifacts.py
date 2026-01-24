"""Helpers for saving artifacts and generating URLs."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

ARTIFACTS_DIR = Path(os.environ.get("JANUS_ARTIFACTS_DIR", "/workspace/artifacts"))
ARTIFACT_URL_BASE = os.environ.get("JANUS_ARTIFACT_URL_BASE", "/artifacts")


def save_artifact(filename: str, content: bytes | str, mime_type: str | None = None) -> str:
    """Save content as an artifact and return its URL."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = ARTIFACTS_DIR / filename

    if isinstance(content, str):
        filepath.write_text(content, encoding="utf-8")
    else:
        filepath.write_bytes(content)

    return f"{ARTIFACT_URL_BASE.rstrip('/')}/{filename}"


def artifact_to_base64(filepath: str) -> str:
    """Convert a file to a base64 data URL."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    mime_type, _ = mimetypes.guess_type(str(path))
    mime_type = mime_type or "application/octet-stream"

    content = path.read_bytes()
    b64 = base64.b64encode(content).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def create_download_link(filename: str, display_name: str | None = None) -> str:
    """Create a markdown download link for an artifact."""
    display = display_name or filename
    url = f"{ARTIFACT_URL_BASE.rstrip('/')}/{filename}"
    return f"[{display}]({url})"


def create_image_embed(filename: str, alt_text: str = "Image") -> str:
    """Create markdown image embed for an artifact."""
    filepath = ARTIFACTS_DIR / filename
    if filepath.exists() and filepath.stat().st_size < 500_000:
        data_url = artifact_to_base64(str(filepath))
        return f"![{alt_text}]({data_url})"
    url = f"{ARTIFACT_URL_BASE.rstrip('/')}/{filename}"
    return f"![{alt_text}]({url})"
