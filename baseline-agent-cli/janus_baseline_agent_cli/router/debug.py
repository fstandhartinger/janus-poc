"""Debug event streaming routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from janus_baseline_agent_cli.services.debug import debug_queue

router = APIRouter(prefix="/v1/debug", tags=["debug"])


@router.get("/stream/{request_id}")
async def stream_debug(request_id: str) -> StreamingResponse:
    async def event_generator():
        async for event in debug_queue.subscribe(request_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
