from typing import Iterable, List, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.schemas import Memory, MemoryExtraction
from memory_service.services.llm import ExtractedMemory
from memory_service.utils import generate_memory_id


async def was_conversation_processed(
    session: AsyncSession, user_id: UUID, conversation_hash: str
) -> bool:
    result = await session.execute(
        select(MemoryExtraction.id).where(
            MemoryExtraction.user_id == user_id,
            MemoryExtraction.conversation_hash == conversation_hash,
        )
    )
    return result.first() is not None


async def record_extraction(
    session: AsyncSession, user_id: UUID, conversation_hash: str, count: int
) -> None:
    extraction = MemoryExtraction(
        user_id=user_id, conversation_hash=conversation_hash, memories_extracted=count
    )
    session.add(extraction)
    await session.commit()


async def count_memories(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(Memory).where(Memory.user_id == user_id)
    )
    return int(result.scalar_one())


async def list_memories(
    session: AsyncSession, user_id: UUID, limit: int, offset: int
) -> List[Memory]:
    result = await session.execute(
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_memory_captions(session: AsyncSession, user_id: UUID) -> List[tuple[str, str]]:
    result = await session.execute(
        select(Memory.id, Memory.caption)
        .where(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_memories_by_ids(
    session: AsyncSession, user_id: UUID, ids: Sequence[str]
) -> List[Memory]:
    if not ids:
        return []
    result = await session.execute(
        select(Memory)
        .where(Memory.user_id == user_id, Memory.id.in_(ids))
        .order_by(Memory.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_memory(session: AsyncSession, user_id: UUID, memory_id: str) -> bool:
    result = await session.execute(
        delete(Memory).where(Memory.user_id == user_id, Memory.id == memory_id)
    )
    await session.commit()
    return result.rowcount > 0


async def save_memories(
    session: AsyncSession,
    user_id: UUID,
    memories: Iterable[ExtractedMemory],
    max_memories: int,
) -> List[Memory]:
    created: List[Memory] = []
    for mem in memories:
        entry = Memory(
            id=generate_memory_id(),
            user_id=user_id,
            caption=mem.caption,
            full_text=mem.full_text,
        )
        session.add(entry)
        created.append(entry)

    await session.flush()
    for entry in created:
        await session.refresh(entry)

    await _trim_oldest(session, user_id, max_memories)
    await session.commit()
    return created


async def _trim_oldest(session: AsyncSession, user_id: UUID, max_memories: int) -> None:
    if max_memories <= 0:
        return
    count = await count_memories(session, user_id)
    if count <= max_memories:
        return

    result = await session.execute(
        select(Memory.id)
        .where(Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .offset(max_memories)
    )
    ids_to_delete = [row[0] for row in result.all()]
    if ids_to_delete:
        await session.execute(delete(Memory).where(Memory.id.in_(ids_to_delete)))
