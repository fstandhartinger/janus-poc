"""Tests for memory integration helpers."""

import asyncio
import pytest

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.main import _inject_memory_context, chat_completions
from janus_baseline_langchain.models import (
    ChatCompletionRequest,
    ImageUrl,
    ImageUrlContent,
    Message,
    MessageRole,
    TextContent,
    Tool,
)
from janus_baseline_langchain.models.openai import FunctionDefinition


def test_inject_memory_context_preserves_images() -> None:
    """Memory context should preserve image parts in multimodal messages."""
    messages = [
        Message(
            role=MessageRole.USER,
            content=[
                TextContent(text="Describe this"),
                ImageUrlContent(image_url=ImageUrl(url="https://example.com/img.png")),
            ],
        )
    ]

    _inject_memory_context(messages, "MEMORY")

    content = messages[0].content
    assert isinstance(content, list)
    assert isinstance(content[0], TextContent)
    assert content[0].text == "MEMORY"
    assert any(isinstance(part, ImageUrlContent) for part in content)


@pytest.mark.asyncio
async def test_memory_extraction_triggered_on_tool_call() -> None:
    """Memory extraction should run for non-streaming tool responses."""

    class DummyMemoryService:
        def __init__(self) -> None:
            self.event = asyncio.Event()
            self.conversation = []

        async def get_memory_context(self, user_id: str, prompt: str) -> str:
            return ""

        async def extract_memories(self, user_id: str, conversation):
            self.conversation = conversation
            self.event.set()

    settings = Settings()
    memory_service = DummyMemoryService()
    request = ChatCompletionRequest(
        model="baseline-langchain",
        messages=[Message(role=MessageRole.USER, content="What's the weather in Paris?")],
        stream=False,
        tools=[
            Tool(
                function=FunctionDefinition(
                    name="get_weather",
                    description="Get weather",
                    parameters={"type": "object", "properties": {}},
                )
            )
        ],
        enable_memory=True,
        user_id="user-1",
    )

    response = await chat_completions(
        request,
        settings=settings,
        memory_service=memory_service,
    )

    assert response.choices[0].message.tool_calls is not None

    await asyncio.wait_for(memory_service.event.wait(), timeout=1.0)
    assert memory_service.conversation
    assert memory_service.conversation[-1]["role"] == "assistant"
