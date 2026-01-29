"""Unit tests for Sandy service helpers."""

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import ChatCompletionRequest, Message, MessageRole
from janus_baseline_agent_cli.services.sandy import SandyService


def test_extract_task_text_content() -> None:
    service = SandyService(Settings())
    request = ChatCompletionRequest(
        model="baseline",
        messages=[Message(role=MessageRole.USER, content="Write hello world")],
    )
    task = service._extract_task(request)
    assert "hello world" in task.lower()


def test_extract_task_multimodal_content() -> None:
    service = SandyService(Settings())
    request = ChatCompletionRequest(
        model="baseline",
        messages=[
            Message(
                role=MessageRole.USER,
                content=[
                    {"type": "text", "text": "Analyze this"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                ],
            )
        ],
    )
    task = service._extract_task(request)
    assert "Analyze this" in task
    assert "image" in task.lower()
