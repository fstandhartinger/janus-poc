"""OpenAI-compatible request/response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr


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


class FunctionDefinition(BaseModel):
    """OpenAI function definition."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolDefinition(BaseModel):
    """OpenAI tool definition."""

    type: Literal["function"] = "function"
    function: FunctionDefinition


class FunctionCall(BaseModel):
    """Function call in tool_calls."""

    name: str
    arguments: str  # JSON string


class ToolCall(BaseModel):
    """Tool call in assistant message."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class ArtifactType(str, Enum):
    """Artifact types."""

    IMAGE = "image"
    FILE = "file"
    DATASET = "dataset"
    BINARY = "binary"


class Artifact(BaseModel):
    """Artifact descriptor for non-text outputs."""

    id: str
    type: ArtifactType
    mime_type: str
    display_name: str
    size_bytes: int
    sha256: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    ttl_seconds: int = 3600
    url: str


class AssistantMessage(BaseModel):
    """Assistant message with optional tool calls."""

    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    artifacts: Optional[list[Artifact]] = None
    tool_calls: Optional[list[ToolCall]] = None


class StreamOptions(BaseModel):
    """Streaming options."""

    include_usage: Optional[bool] = None


class GenerationFlags(BaseModel):
    """Optional generation flags for agent routing."""

    generate_image: bool = False
    generate_video: bool = False
    generate_audio: bool = False
    deep_research: bool = False
    web_search: bool = False


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    _auth_token: Optional[str] = PrivateAttr(default=None)

    model: str
    messages: list[Message]
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stream: Optional[bool] = False
    stream_options: Optional[StreamOptions] = None
    tools: Optional[list[ToolDefinition]] = None
    tool_choice: Optional[Union[str, dict[str, Any]]] = None
    user: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    user_id: Optional[str] = None
    enable_memory: bool = False
    chutes_access_token: Optional[str] = None
    generation_flags: Optional[GenerationFlags] = None


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
    message: Union[Message, AssistantMessage]
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
    tool_calls: Optional[list[ToolCall]] = None
    janus: Optional[dict[str, Any]] = None


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
    metadata: Optional[dict[str, Any]] = None
    choices: list[ChunkChoice]
    usage: Optional[Usage] = None
