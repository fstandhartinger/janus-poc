"""Unit tests for OpenAI models."""

import pytest

from janus_gateway.models import (
    Artifact,
    ArtifactType,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    MessageRole,
    Usage,
)


def test_minimal_request_defaults() -> None:
    request = ChatCompletionRequest(
        model="baseline-cli-agent",
        messages=[Message(role=MessageRole.USER, content="Hello")],
    )
    assert request.model == "baseline-cli-agent"
    assert len(request.messages) == 1
    assert request.stream is False


def test_request_with_optional_fields() -> None:
    request = ChatCompletionRequest(
        model="baseline-cli-agent",
        messages=[Message(role=MessageRole.USER, content="Hello")],
        temperature=0.7,
        top_p=0.9,
        max_tokens=1000,
        stream=True,
        user="user-123",
        metadata={"session": "abc"},
    )
    assert request.temperature == 0.7
    assert request.stream is True


def test_text_only_message() -> None:
    msg = Message(role=MessageRole.USER, content="Hello world")
    assert msg.content == "Hello world"


def test_multimodal_message_with_image() -> None:
    request = ChatCompletionRequest(
        model="baseline-cli-agent",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}},
                ],
            )
        ],
    )
    assert isinstance(request.messages[0].content, list)
    assert len(request.messages[0].content) == 2


def test_system_and_assistant_messages() -> None:
    request = ChatCompletionRequest(
        model="baseline",
        messages=[
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi!"),
        ],
    )
    assert request.messages[0].role == MessageRole.SYSTEM
    assert request.messages[2].role == MessageRole.ASSISTANT


def test_tool_message() -> None:
    request = ChatCompletionRequest(
        model="baseline",
        messages=[
            Message(role=MessageRole.USER, content="What's 2+2?"),
            Message(role=MessageRole.TOOL, content="4", tool_call_id="call_123"),
        ],
    )
    assert request.messages[1].role == MessageRole.TOOL
    assert request.messages[1].tool_call_id == "call_123"


def test_empty_messages_rejected() -> None:
    with pytest.raises(ValueError):
        ChatCompletionRequest(model="baseline", messages=[])


def test_temperature_bounds() -> None:
    ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hi")],
        temperature=0.0,
    )
    ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Hi")],
        temperature=2.0,
    )
    with pytest.raises(ValueError):
        ChatCompletionRequest(
            model="baseline",
            messages=[Message(role=MessageRole.USER, content="Hi")],
            temperature=-0.1,
        )


def test_unicode_content_handling() -> None:
    text = "\u3053\u3093\u306b\u3061\u306f"
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content=text)],
    )
    assert request.messages[0].content == text


def test_response_structure() -> None:
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        model="baseline-cli-agent",
        choices=[
            Choice(
                index=0,
                message=Message(role=MessageRole.ASSISTANT, content="Hello!"),
            )
        ],
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    assert response.id.startswith("chatcmpl-")
    assert len(response.choices) == 1


def test_response_with_artifacts() -> None:
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        model="baseline",
        choices=[
            Choice(
                index=0,
                message=Message(
                    role=MessageRole.ASSISTANT,
                    content="Here's your image:",
                    artifacts=[
                        Artifact(
                            id="artifact-1",
                            type=ArtifactType.IMAGE,
                            mime_type="image/png",
                            display_name="Generated Image",
                            size_bytes=123,
                            url="https://example.com/image.png",
                        )
                    ],
                ),
            )
        ],
    )
    assert response.choices[0].message.artifacts is not None
    assert response.choices[0].message.artifacts[0].type == ArtifactType.IMAGE
