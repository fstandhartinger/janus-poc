"""Tests for message preprocessing."""

from janus_gateway.models.openai import FileContent, FileInfo, Message, MessageRole
from janus_gateway.services.message_processor import MessageProcessor


def test_message_processor_converts_file_part_to_text() -> None:
    processor = MessageProcessor()
    message = Message(
        role=MessageRole.USER,
        content=[
            FileContent(
                file=FileInfo(
                    name="notes.txt",
                    mime_type="text/plain",
                    content="Hello from file",
                    size=17,
                )
            )
        ],
    )
    processed = processor.process_message(message)
    assert isinstance(processed.content, list)
    assert processed.content[0].type == "text"
    assert "Hello from file" in processed.content[0].text
