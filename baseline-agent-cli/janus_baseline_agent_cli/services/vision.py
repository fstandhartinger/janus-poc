"""Vision utilities for detecting image content in messages."""

from typing import Union

from janus_baseline_agent_cli.models import ImageUrlContent, Message, MessageContent


def has_image_content(content: Union[MessageContent, None]) -> bool:
    """Check if message content contains images."""
    if content is None or isinstance(content, str):
        return False

    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "image_url":
                return True
        elif isinstance(part, ImageUrlContent):
            return True

    return False


def contains_images(messages: list[Message]) -> bool:
    """Check if any message contains image content."""
    return any(has_image_content(message.content) for message in messages)


def count_images(messages: list[Message]) -> int:
    """Count total images across all messages."""
    count = 0
    for message in messages:
        content = message.content
        if content and not isinstance(content, str):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    count += 1
                elif isinstance(part, ImageUrlContent):
                    count += 1
    return count


def get_image_urls(message: Message) -> list[str]:
    """Extract image URLs from a message."""
    urls: list[str] = []
    content = message.content
    if content and not isinstance(content, str):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                if url:
                    urls.append(url)
            elif isinstance(part, ImageUrlContent):
                urls.append(part.image_url.url)
    return urls
