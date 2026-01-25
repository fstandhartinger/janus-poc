import logging
import time
from collections import defaultdict, deque
from typing import Deque, List
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.config import get_settings
from memory_service.database import close_db, get_session, init_db
from memory_service.models import (
    DeleteMemoryResponse,
    ExtractMemoriesRequest,
    ExtractMemoriesResponse,
    MemoryExtracted,
    MemoryFull,
    MemoryFullResponse,
    MemoryListResponse,
    MemorySummary,
    RelevantMemoriesResponse,
)
from memory_service.services import llm, memory
from memory_service.utils import hash_conversation

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("memory_service")

app = FastAPI(title="Janus Memory Service", version="1.0.0")
_rate_limit: dict[str, Deque[float]] = defaultdict(deque)


@app.on_event("startup")
async def startup() -> None:
    if settings.init_db:
        await init_db()


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_db()


def _check_rate_limit(user_id: UUID) -> None:
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_per_minute
    now = time.monotonic()
    history = _rate_limit[str(user_id)]
    while history and now - history[0] > window:
        history.popleft()
    if len(history) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    history.append(now)


def _serialize_memories(memories: List) -> List[MemoryFull]:
    return [
        MemoryFull(
            id=mem.id,
            caption=mem.caption,
            full_text=mem.full_text,
            created_at=mem.created_at,
        )
        for mem in memories
    ]


@app.post("/memories/extract", response_model=ExtractMemoriesResponse)
async def extract_memories(
    request: ExtractMemoriesRequest,
    session: AsyncSession = Depends(get_session),
) -> ExtractMemoriesResponse:
    _check_rate_limit(request.user_id)

    conversation_payload = [msg.model_dump() for msg in request.conversation]
    conversation_hash = hash_conversation(conversation_payload)

    if await memory.was_conversation_processed(session, request.user_id, conversation_hash):
        total = await memory.count_memories(session, request.user_id)
        return ExtractMemoriesResponse(memories_saved=[], total_user_memories=total)

    if not conversation_payload or all(
        not msg.get("content", "").strip() for msg in conversation_payload
    ):
        await memory.record_extraction(session, request.user_id, conversation_hash, 0)
        total = await memory.count_memories(session, request.user_id)
        return ExtractMemoriesResponse(memories_saved=[], total_user_memories=total)

    extracted = await llm.extract_memories(conversation_payload)
    saved = []
    if extracted:
        saved = await memory.save_memories(
            session,
            request.user_id,
            extracted,
            settings.max_memories_per_user,
        )

    await memory.record_extraction(session, request.user_id, conversation_hash, len(saved))
    total = await memory.count_memories(session, request.user_id)
    return ExtractMemoriesResponse(
        memories_saved=[
            MemoryExtracted(id=mem.id, caption=mem.caption, created_at=mem.created_at)
            for mem in saved
        ],
        total_user_memories=total,
    )


@app.get("/memories/relevant", response_model=RelevantMemoriesResponse)
async def get_relevant_memories(
    user_id: UUID = Query(...),
    prompt: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> RelevantMemoriesResponse:
    _check_rate_limit(user_id)

    memories = await memory.list_memory_captions(session, user_id)
    if not memories or not prompt.strip():
        return RelevantMemoriesResponse(memories=[])

    relevant_ids = await llm.select_relevant_ids(prompt, memories)
    if not relevant_ids:
        return RelevantMemoriesResponse(memories=[])

    caption_map = {mem_id: caption for mem_id, caption in memories}
    results = [
        MemorySummary(id=mem_id, caption=caption_map[mem_id])
        for mem_id in relevant_ids
        if mem_id in caption_map
    ]
    return RelevantMemoriesResponse(memories=results)


@app.get("/memories/full", response_model=MemoryFullResponse)
async def get_full_memories(
    user_id: UUID = Query(...),
    ids: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> MemoryFullResponse:
    _check_rate_limit(user_id)

    requested_ids = [value.strip() for value in ids.split(",") if value.strip()]
    memories = await memory.get_memories_by_ids(session, user_id, requested_ids)
    return MemoryFullResponse(memories=_serialize_memories(memories))


@app.delete("/memories/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str,
    user_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> DeleteMemoryResponse:
    _check_rate_limit(user_id)

    deleted = await memory.delete_memory(session, user_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return DeleteMemoryResponse(status="deleted")


@app.get("/memories/list", response_model=MemoryListResponse)
async def list_memories(
    user_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> MemoryListResponse:
    _check_rate_limit(user_id)

    memories = await memory.list_memories(session, user_id, limit, offset)
    return MemoryListResponse(memories=_serialize_memories(memories))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "janus-memory"}
