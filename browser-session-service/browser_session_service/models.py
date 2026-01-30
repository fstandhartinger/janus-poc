"""Pydantic models for API requests and responses."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# Domain validation regex
DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)

# Session name validation: alphanumeric + dashes + underscores
SESSION_NAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class StorageState(BaseModel):
    """Playwright-compatible storage state format."""

    cookies: List[Dict[str, Any]] = Field(default_factory=list)
    origins: List[Dict[str, Any]] = Field(default_factory=list)


class SessionCreate(BaseModel):
    """Request model for creating a new session."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="User-provided session name (alphanumeric, dashes, underscores)",
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Optional session description"
    )
    domains: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Domains covered by this session",
    )
    storage_state: StorageState = Field(
        ..., description="Playwright storage state with cookies and origins"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration timestamp"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not SESSION_NAME_REGEX.match(v):
            raise ValueError(
                "Session name must start with alphanumeric and contain only "
                "alphanumeric characters, dashes, and underscores"
            )
        return v

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        for domain in v:
            if not DOMAIN_REGEX.match(domain):
                raise ValueError(f"Invalid domain format: {domain}")
        return v


class SessionUpdate(BaseModel):
    """Request model for updating a session."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    storage_state: Optional[StorageState] = None
    expires_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not SESSION_NAME_REGEX.match(v):
            raise ValueError(
                "Session name must start with alphanumeric and contain only "
                "alphanumeric characters, dashes, and underscores"
            )
        return v


class SessionSummary(BaseModel):
    """Summary response for a session (without storage state)."""

    id: str
    name: str
    description: Optional[str]
    domains: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: List[SessionSummary]


class SessionStateResponse(BaseModel):
    """Response for getting session storage state."""

    storage_state: StorageState


class SessionCreateResponse(BaseModel):
    """Response for creating a session."""

    id: str
    name: str
    description: Optional[str]
    domains: List[str]
    expires_at: Optional[datetime]
    created_at: datetime


class DeleteResponse(BaseModel):
    """Response for delete operations."""

    status: str = "deleted"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
