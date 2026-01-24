"""Unit tests for message content parsing."""

from janus_baseline_agent_cli.models import ImageUrl, ImageUrlContent, Message, MessageRole, TextContent
from janus_baseline_agent_cli.models.utils import extract_images, extract_text_content


def test_parse_text_content() -> None:
    """Parse simple text content."""
    msg = Message(role=MessageRole.USER, content="Hello")
    assert msg.content == "Hello"


def test_parse_multimodal_content() -> None:
    """Parse multimodal content array."""
    content = [
        TextContent(text="What's this?"),
        ImageUrlContent(image_url=ImageUrl(url="data:image/png;base64,abc")),
    ]
    msg = Message(role=MessageRole.USER, content=content)
    assert msg.content
    assert len(msg.content) == 2


def test_extract_text_from_multimodal() -> None:
    """Extract text from multimodal message."""
    content = [
        TextContent(text="Describe this"),
        ImageUrlContent(image_url=ImageUrl(url="data:image/png;base64,abc")),
    ]
    text = extract_text_content(content)
    assert text == "Describe this"


def test_extract_images_from_multimodal() -> None:
    """Extract images from multimodal message."""
    content = [
        TextContent(text="Describe this"),
        ImageUrlContent(image_url=ImageUrl(url="data:image/png;base64,abc123")),
    ]
    images = extract_images(content)
    assert images == ["data:image/png;base64,abc123"]
