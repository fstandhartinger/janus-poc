"""Memory management proxy routes."""

from typing import Any, cast

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from janus_gateway.config import get_settings

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryUpdateRequest(BaseModel):
    user_id: str
    caption: str | None = None
    full_text: str | None = None


def _memory_base_url() -> str:
    return get_settings().memory_service_url.rstrip("/")


async def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    detail = response.text or "Upstream error"
    raise HTTPException(status_code=response.status_code, detail=detail)


@router.get("")
async def list_memories(
    user_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List all memories for a user."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{_memory_base_url()}/memories/list",
            params={"user_id": user_id, "limit": limit, "offset": offset},
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdateRequest) -> dict[str, Any]:
    """Update a memory."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.patch(
            f"{_memory_base_url()}/memories/{memory_id}",
            json=body.model_dump(exclude_none=True),
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.delete("/clear")
async def clear_memories(user_id: str = Query(...)) -> dict[str, Any]:
    """Clear all memories for a user."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{_memory_base_url()}/memories/clear",
            params={"user_id": user_id},
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str = Query(...),
) -> dict[str, Any]:
    """Delete a memory."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.delete(
            f"{_memory_base_url()}/memories/{memory_id}",
            params={"user_id": user_id},
        )
        await _raise_for_status(response)
        return cast(dict[str, Any], response.json())
