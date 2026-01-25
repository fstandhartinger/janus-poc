import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from memory_service.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    caption: Mapped[str] = mapped_column(String(100), nullable=False)
    full_text: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


class MemoryExtraction(Base):
    __tablename__ = "memory_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    conversation_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    memories_extracted: Mapped[int] = mapped_column(Integer, server_default="0")
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )


Index("idx_memories_user_id", Memory.user_id)
Index("idx_memories_created_at", Memory.created_at.desc())
Index("idx_memory_extractions_user_id", MemoryExtraction.user_id)
Index("idx_memory_extractions_conversation_hash", MemoryExtraction.conversation_hash)
