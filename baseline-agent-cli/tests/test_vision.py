"""Tests for vision detection and routing utilities."""

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import (
    ChatCompletionRequest,
    ImageUrl,
    ImageUrlContent,
    Message,
    MessageRole,
    TextContent,
)
from janus_baseline_agent_cli.services.llm import LLMService
from janus_baseline_agent_cli.services.vision import (
    contains_images,
    count_images,
    get_image_urls,
    has_image_content,
)


def test_has_image_content_dict() -> None:
    content = [
        {"type": "text", "text": "Hello"},
        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
    ]
    assert has_image_content(content) is True


def test_has_image_content_model() -> None:
    content = [TextContent(text="Hello"), ImageUrlContent(image_url=ImageUrl(url="img"))]
    assert has_image_content(content) is True


def test_contains_images_and_count() -> None:
    messages = [
        Message(role=MessageRole.USER, content="no image"),
        Message(
            role=MessageRole.USER,
            content=[
                {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
            ],
        ),
    ]
    assert contains_images(messages) is True
    assert count_images(messages) == 2


def test_get_image_urls() -> None:
    message = Message(
        role=MessageRole.USER,
        content=[
            {"type": "text", "text": "See"},
            {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
            ImageUrlContent(image_url=ImageUrl(url="https://example.com/b.png")),
        ],
    )
    assert get_image_urls(message) == [
        "https://example.com/a.png",
        "https://example.com/b.png",
    ]


def test_select_model_routes_to_vision() -> None:
    settings = Settings(enable_vision_routing=True, use_model_router=False)
    service = LLMService(settings)
    request = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    TextContent(text="What is this?"),
                    ImageUrlContent(image_url=ImageUrl(url="https://example.com/a.png")),
                ],
            )
        ],
    )
    from janus_baseline_agent_cli.routing import FAST_KIMI_MODEL_ID
    assert service.select_model(request) == FAST_KIMI_MODEL_ID


def test_select_model_respects_disabled_routing() -> None:
    settings = Settings(enable_vision_routing=False, use_model_router=False)
    service = LLMService(settings)
    request = ChatCompletionRequest(
        model="custom-model",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    ImageUrlContent(image_url=ImageUrl(url="https://example.com/a.png")),
                ],
            )
        ],
    )
    from janus_baseline_agent_cli.routing import FAST_KIMI_MODEL_ID
    assert service.select_model(request) == FAST_KIMI_MODEL_ID


def test_select_model_uses_default_for_baseline_alias() -> None:
    settings = Settings(model="gpt-4o-mini", use_model_router=False)
    service = LLMService(settings)
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hello")],
    )
    assert service.select_model(request) == settings.model
