"""Vision utilities for the LangChain baseline."""

from typing import Iterable

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from janus_baseline_langchain.config import Settings, get_settings
from janus_baseline_langchain.models import ImageUrlContent


def create_vision_chain(
    settings: Settings | None = None,
    model: str | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> ChatOpenAI:
    """Create a LangChain model configured for vision requests."""
    settings = settings or get_settings()
    api_key_value = api_key_override or settings.openai_api_key or "dummy-key"
    api_key = SecretStr(api_key_value)
    return ChatOpenAI(
        model=model or settings.vision_model_primary,
        api_key=api_key,
        base_url=base_url_override or settings.openai_base_url,
        temperature=settings.temperature,
        streaming=True,
        max_retries=settings.max_retries,
        timeout=settings.vision_model_timeout,
    )


def has_image_content(content) -> bool:
    """Check if content contains image parts."""
    if content is None or isinstance(content, str):
        return False
    for part in content:
        if isinstance(part, dict) and part.get("type") == "image_url":
            return True
        if isinstance(part, ImageUrlContent):
            return True
    return False


def contains_images(messages: Iterable) -> bool:
    """Check if any message includes image content."""
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else message.content
        if has_image_content(content):
            return True
    return False


def count_images(messages: Iterable) -> int:
    """Count image parts in the provided messages."""
    count = 0
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else message.content
        if content is None or isinstance(content, str):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                count += 1
            elif isinstance(part, ImageUrlContent):
                count += 1
    return count


def convert_to_langchain_messages(messages: list) -> list[BaseMessage]:
    """Convert OpenAI messages to LangChain format, preserving images."""
    lc_messages: list[BaseMessage] = []

    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else msg.role.value
        content = msg.get("content") if isinstance(msg, dict) else msg.content

        if role == "user":
            lc_messages.append(HumanMessage(content=_format_user_content(content)))
        elif role == "assistant":
            text = content if isinstance(content, str) else _extract_text(content)
            lc_messages.append(AIMessage(content=text))
        elif role == "system":
            text = content if isinstance(content, str) else _extract_text(content)
            lc_messages.append(SystemMessage(content=text))
        elif role == "tool":
            text = content if isinstance(content, str) else _extract_text(content)
            tool_id = (
                msg.get("tool_call_id")
                if isinstance(msg, dict)
                else msg.tool_call_id or "tool"
            )
            lc_messages.append(ToolMessage(content=text, tool_call_id=tool_id))

    return lc_messages


def _format_user_content(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content

    formatted: list[dict] = []
    for part in content:
        if isinstance(part, dict):
            formatted.append(part)
        elif hasattr(part, "model_dump"):
            formatted.append(part.model_dump())
        else:
            formatted.append({"type": "text", "text": str(part)})
    return formatted


def _extract_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text", ""))
        elif hasattr(part, "text"):
            parts.append(part.text)
    return " ".join(p for p in parts if p).strip()
