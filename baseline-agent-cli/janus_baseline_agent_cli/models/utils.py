"""Utilities for working with message content."""

from __future__ import annotations

from janus_baseline_agent_cli.models.openai import ImageUrlContent, MessageContent, TextContent


def extract_text_content(content: MessageContent | None) -> str:
    """Extract text from message content."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for part in content:
        if isinstance(part, TextContent):
            parts.append(part.text)
        elif isinstance(part, dict):
            if part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return " ".join(part for part in parts if part).strip()


def extract_images(content: MessageContent | None) -> list[str]:
    """Extract image URLs from message content."""
    if content is None or isinstance(content, str):
        return []

    urls: list[str] = []
    for part in content:
        if isinstance(part, ImageUrlContent):
            urls.append(part.image_url.url)
        elif isinstance(part, dict):
            if part.get("type") == "image_url":
                image_url = part.get("image_url") or {}
                url = image_url.get("url")
                if isinstance(url, str) and url:
                    urls.append(url)
    return urls
