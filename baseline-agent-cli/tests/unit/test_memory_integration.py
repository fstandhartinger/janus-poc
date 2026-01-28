"""Tests for memory integration helpers."""

import asyncio
import pytest

from janus_baseline_agent_cli.main import (
    _apply_memory_tool,
    _build_conversation_base,
    _inject_memory_context,
    stream_response,
)
from janus_baseline_agent_cli.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChunkChoice,
    Delta,
    ImageUrl,
    ImageUrlContent,
    Message,
    MessageRole,
    TextContent,
    ToolDefinition,
)


def test_inject_memory_context_updates_last_user_message() -> None:
    """Memory context should update the most recent user message."""
    messages = [
        Message(role=MessageRole.USER, content="First"),
        Message(role=MessageRole.ASSISTANT, content="Hi"),
        Message(role=MessageRole.USER, content="Second"),
    ]

    _inject_memory_context(messages, "MEMORY")

    assert messages[-1].content == "MEMORY"
    assert messages[0].content == "First"


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


def test_apply_memory_tool_controls_availability() -> None:
    request = ChatCompletionRequest(
        model="test",
        messages=[Message(role=MessageRole.USER, content="Hi")],
        tools=[],
    )

    _apply_memory_tool(request, enable=False)
    assert request.tools is None

    _apply_memory_tool(request, enable=True)
    assert request.tools is not None
    tool = request.tools[0]
    if isinstance(tool, ToolDefinition):
        assert tool.function.name == "investigate_memory"
    else:
        assert tool["function"]["name"] == "investigate_memory"


@pytest.mark.asyncio
async def test_memory_extraction_fires_after_stream() -> None:
    """Memory extraction should be scheduled after streaming completes."""

    class DummyAnalysis:
        is_complex = False
        reason = "simple"
        keywords_matched = []
        multimodal_detected = False
        has_images = False
        image_count = 0
        sandy_available = False
        text_preview = ""

    class DummyDetector:
        async def analyze_async(self, messages, generation_flags=None):
            return DummyAnalysis()

    class DummyLLM:
        async def stream(self, request):
            yield ChatCompletionChunk(
                id="test",
                model=request.model,
                choices=[
                    ChunkChoice(
                        delta=Delta(content="Hello"),
                    )
                ],
            )

    class DummySandy:
        is_available = False

        async def execute_complex(self, request, debug_emitter=None):
            if False:
                yield

    class DummyMemoryService:
        def __init__(self) -> None:
            self.event = asyncio.Event()
            self.conversation = []

        async def extract_memories(self, user_id: str, conversation):
            self.conversation = conversation
            self.event.set()

    request = ChatCompletionRequest(
        model="test",
        messages=[Message(role=MessageRole.USER, content="Hi")],
        stream=True,
    )
    conversation_base = _build_conversation_base(request.messages)
    memory_service = DummyMemoryService()

    async for _ in stream_response(
        request,
        DummyDetector(),
        DummyLLM(),
        DummySandy(),
        memory_service=memory_service,
        memory_user_id="user-1",
        conversation_base=conversation_base,
    ):
        pass

    await asyncio.wait_for(memory_service.event.wait(), timeout=1.0)
    assert memory_service.conversation[-1]["content"] == "Hello"
