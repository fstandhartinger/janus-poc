"""Helpers for post-processing agent responses."""

from __future__ import annotations

import re

_ARTIFACT_LINK_PATTERN = re.compile(r"(\[.*?\]\()/artifacts/([^)]+)\)")


def resolve_artifact_urls(content: str, artifact_base_url: str) -> str:
    """Resolve relative /artifacts/ links to absolute artifact URLs."""
    if not content or not artifact_base_url:
        return content

    base = artifact_base_url.rstrip("/")

    def replace_url(match: re.Match) -> str:
        prefix = match.group(1)
        filename = match.group(2)
        return f"{prefix}{base}/{filename})"

    return _ARTIFACT_LINK_PATTERN.sub(replace_url, content)


def process_agent_response(
    content: str,
    sandbox_url: str | None,
    gateway_url: str | None = None,
) -> str:
    """Resolve relative URLs in agent output before returning to clients."""
    if not content:
        return content

    if sandbox_url:
        content = resolve_artifact_urls(content, f"{sandbox_url.rstrip('/')}/artifacts")

    return content
