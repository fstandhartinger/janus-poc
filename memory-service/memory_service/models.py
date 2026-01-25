from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str
    content: str


class ExtractMemoriesRequest(BaseModel):
    user_id: UUID
    conversation: List[ConversationMessage]


class MemorySummary(BaseModel):
    id: str
    caption: str


class MemoryExtracted(BaseModel):
    id: str
    caption: str
    created_at: datetime


class ExtractMemoriesResponse(BaseModel):
    memories_saved: List[MemoryExtracted] = Field(default_factory=list)
    total_user_memories: int


class RelevantMemoriesResponse(BaseModel):
    memories: List[MemorySummary] = Field(default_factory=list)


class MemoryFull(BaseModel):
    id: str
    caption: str
    full_text: str
    created_at: datetime


class MemoryFullResponse(BaseModel):
    memories: List[MemoryFull] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    memories: List[MemoryFull] = Field(default_factory=list)


class DeleteMemoryResponse(BaseModel):
    status: str
