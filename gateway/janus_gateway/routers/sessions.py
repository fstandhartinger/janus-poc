"""Browser session management proxy routes."""

from typing import Any, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from janus_gateway.config import Settings, get_settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Timeout for session service requests
SESSION_TIMEOUT = 30.0


class SessionCreateRequest(BaseModel):
    """Request to create a new browser session."""
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    domains: list[str] = Field(..., min_length=1)
    storage_state: dict[str, Any]
    expires_at: str | None = None


class SessionUpdateRequest(BaseModel):
    """Request to update a browser session."""
    name: str | None = None
    description: str | None = None
    storage_state: dict[str, Any] | None = None
    expires_at: str | None = None


def _session_base_url(settings: Settings) -> str:
    """Get the session service base URL."""
    return settings.session_service_url.rstrip("/")


def _get_auth_header(request: Request) -> dict[str, str]:
    """Extract authorization header from request."""
    auth_header = request.headers.get("authorization")
    if auth_header:
        return {"Authorization": auth_header}
    return {}


async def _raise_for_status(response: httpx.Response) -> None:
    """Raise HTTPException for non-success responses."""
    if response.is_success:
        return
    detail = response.text or "Upstream error"
    raise HTTPException(status_code=response.status_code, detail=detail)


@router.get("")
async def list_sessions(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """List all browser sessions for the authenticated user."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.get(
            f"{_session_base_url(settings)}/sessions",
            headers=_get_auth_header(request),
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.post("")
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Create a new browser session."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.post(
            f"{_session_base_url(settings)}/sessions",
            json=body.model_dump(exclude_none=True),
            headers={
                **_get_auth_header(request),
                "Content-Type": "application/json",
            },
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get session details (without storage state)."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.get(
            f"{_session_base_url(settings)}/sessions/{session_id}",
            headers=_get_auth_header(request),
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.get("/{session_id}/state")
async def get_session_state(
    session_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get the decrypted storage state for a session."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.get(
            f"{_session_base_url(settings)}/sessions/{session_id}/state",
            headers=_get_auth_header(request),
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    body: SessionUpdateRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Update a session's metadata or storage state."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.put(
            f"{_session_base_url(settings)}/sessions/{session_id}",
            json=body.model_dump(exclude_none=True),
            headers={
                **_get_auth_header(request),
                "Content-Type": "application/json",
            },
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Delete a session."""
    async with httpx.AsyncClient(timeout=SESSION_TIMEOUT) as client:
        response = await client.delete(
            f"{_session_base_url(settings)}/sessions/{session_id}",
            headers=_get_auth_header(request),
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())
