"""OpenAI-compatible request/response models for Chat Completions API."""

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


class FileInfo(BaseModel):
    """File content metadata."""

    name: str
    mime_type: str
    content: str
    size: int


class FileContent(BaseModel):
    """File content part."""

    type: Literal["file"] = "file"
    file: FileInfo


# Content can be string or list of content parts
MessageContent = Union[str, list[Union[TextContent, ImageUrlContent, FileContent]]]


class FunctionCall(BaseModel):
    """Function call information."""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call from the model."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class Message(BaseModel):
    """Chat message."""

    role: MessageRole
    content: Optional[MessageContent] = None
    name: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None


class FunctionDefinition(BaseModel):
    """Function definition for tool."""

    name: str
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    strict: Optional[bool] = None


class Tool(BaseModel):
    """Tool definition."""

    type: Literal["function"] = "function"
    function: FunctionDefinition


class ResponseFormat(BaseModel):
    """Response format specification."""

    type: Literal["text", "json_object", "json_schema"] = "text"
    json_schema: Optional[dict[str, Any]] = None


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
    tools: Optional[list[Tool]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    response_format: Optional[ResponseFormat] = None
    user: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    # Janus extension: select competitor
    competitor_id: Optional[str] = None


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    # Janus extensions
    cost_usd: Optional[float] = None
    sandbox_seconds: Optional[float] = None


class FinishReason(str, Enum):
    """Completion finish reasons."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"


class Choice(BaseModel):
    """Non-streaming response choice."""

    index: int = 0
    message: Message
    finish_reason: Optional[FinishReason] = None
    logprobs: Optional[Any] = None


class ChatCompletionResponse(BaseModel):
    """Non-streaming chat completion response."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[Choice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None


class Delta(BaseModel):
    """Streaming delta content."""

    role: Optional[MessageRole] = None
    content: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    # Janus extensions
    reasoning_content: Optional[str] = None
    janus: Optional[dict[str, Any]] = None


class ChunkChoice(BaseModel):
    """Streaming response choice."""

    index: int = 0
    delta: Delta
    finish_reason: Optional[FinishReason] = None
    logprobs: Optional[Any] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chat completion chunk."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: list[ChunkChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None
