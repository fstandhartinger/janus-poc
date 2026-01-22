"""Janus-specific models and extensions."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


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


class JanusEventType(str, Enum):
    """Janus streaming event types."""

    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    SANDBOX_START = "sandbox_start"
    SANDBOX_END = "sandbox_end"


class JanusEvent(BaseModel):
    """Structured Janus event for streaming."""

    event: JanusEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class CompetitorInfo(BaseModel):
    """Competitor registry entry."""

    id: str
    name: str
    description: Optional[str] = None
    url: str
    enabled: bool = True
    is_baseline: bool = False


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelInfo(BaseModel):
    """Model information for /v1/models endpoint."""

    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    owned_by: str = "janus"


class ModelsResponse(BaseModel):
    """Response for /v1/models endpoint."""

    object: str = "list"
    data: list[ModelInfo]
