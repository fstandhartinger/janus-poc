"""Message preprocessing for file attachments."""

from typing import Any, TypeGuard

from janus_gateway.models.openai import FileContent, Message, TextContent
from janus_gateway.services.file_extractor import FileExtractor


class MessageProcessor:
    """Process messages to extract file contents and prepare for LLM."""

    def __init__(self) -> None:
        self.file_extractor = FileExtractor()

    def process_message(self, message: Message) -> Message:
        """Convert file content parts into text parts."""
        if isinstance(message.content, str) or message.content is None:
            return message

        if not message.content:
            return message

        processed_parts: list[Any] = []

        for part in message.content:
            if self._is_file_part(part):
                if isinstance(part, FileContent):
                    file_info = part.file
                    name = file_info.name
                    mime_type = file_info.mime_type
                    content = file_info.content
                else:
                    file_info = part.get("file", {})
                    name = file_info.get("name", "unknown")
                    mime_type = file_info.get("mime_type", "")
                    content = file_info.get("content", "")

                extracted = self.file_extractor.extract(
                    content=content,
                    mime_type=mime_type,
                    filename=name,
                )
                processed_parts.append(
                    TextContent(
                        text=(
                            f"\n[Attached file: {name}]\n"
                            f"{extracted}\n[End of file]\n"
                        )
                    )
                )
            else:
                processed_parts.append(part)

        return message.model_copy(update={"content": processed_parts})

    @staticmethod
    def _is_file_part(part: Any) -> TypeGuard[FileContent | dict[str, Any]]:
        return isinstance(part, FileContent) or (
            isinstance(part, dict) and part.get("type") == "file"
        )
