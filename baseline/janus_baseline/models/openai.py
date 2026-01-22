"""OpenAI-compatible request/response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Supported message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TextContent(BaseModel):
    """Text content part."""

    type: Literal["text"] = "text"
    text: str


class ImageUrl(BaseModel):
    """Image URL reference."""

    url: str
    detail: Optional[Literal["auto", "low", "high"]] = "auto"


class ImageUrlContent(BaseModel):
    """Image URL content part."""

    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl


MessageContent = Union[str, list[Union[TextContent, ImageUrlContent]]]


class Message(BaseModel):
    """Chat message."""

    role: MessageRole
    content: Optional[MessageContent] = None
    name: Optional[str] = None


class StreamOptions(BaseModel):
    """Streaming options."""

    include_usage: Optional[bool] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str
    messages: list[Message]
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: Optional[bool] = False
    stream_options: Optional[StreamOptions] = None
    user: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class FinishReason(str, Enum):
    """Completion finish reasons."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Optional[float] = None
    sandbox_seconds: Optional[float] = None


class Choice(BaseModel):
    """Non-streaming response choice."""

    index: int = 0
    message: Message
    finish_reason: Optional[FinishReason] = None


class ChatCompletionResponse(BaseModel):
    """Non-streaming chat completion response."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[Choice]
    usage: Optional[Usage] = None


class Delta(BaseModel):
    """Streaming delta content."""

    role: Optional[MessageRole] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None


class ChunkChoice(BaseModel):
    """Streaming response choice."""

    index: int = 0
    delta: Delta
    finish_reason: Optional[FinishReason] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[ChunkChoice]
    usage: Optional[Usage] = None
