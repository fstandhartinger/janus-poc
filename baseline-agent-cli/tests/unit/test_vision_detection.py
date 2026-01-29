"""Unit tests for vision utilities."""

from janus_baseline_agent_cli.models import Message, MessageRole
from janus_baseline_agent_cli.services.vision import contains_images, count_images, get_image_urls, has_image_content


def test_base64_image_detected() -> None:
    messages = [
        Message(
            role=MessageRole.USER,
            content=[
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}},
            ],
        )
    ]
    assert contains_images(messages) is True
    assert count_images(messages) == 1


def test_get_image_urls_from_parts() -> None:
    message = Message(
        role=MessageRole.USER,
        content=[
            {"type": "text", "text": "Compare these:"},
            {"type": "image_url", "image_url": {"url": "https://a.png"}},
            {"type": "image_url", "image_url": {"url": "https://b.png"}},
        ],
    )
    urls = get_image_urls(message)
    assert urls == ["https://a.png", "https://b.png"]


def test_none_content_no_images() -> None:
    assert has_image_content(None) is False


def test_empty_list_no_images() -> None:
    assert has_image_content([]) is False
