"""Memory service client for fetching and extracting memories."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from janus_baseline_agent_cli.config import get_settings

logger = structlog.get_logger()


class MemoryReference(BaseModel):
    """Memory reference from the memory service."""

    id: str
    caption: str


class MemoryService:
    """Client for the memory service."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_relevant_memories(self, user_id: str, prompt: str) -> list[MemoryReference]:
        """Fetch memories relevant to the user's prompt."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/memories/relevant",
                    params={"user_id": user_id, "prompt": prompt},
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("memory_fetch_failed", user_id=user_id, error=str(exc))
            return []

        memories = data.get("memories", [])
        if not isinstance(memories, list):
            return []
        results: list[MemoryReference] = []
        for item in memories:
            if isinstance(item, dict):
                try:
                    results.append(MemoryReference(**item))
                except Exception as exc:
                    logger.warning("memory_parse_failed", error=str(exc))
        return results

    async def get_memory_context(self, user_id: str, prompt: str) -> str:
        """Get formatted memory context for injection into prompt."""
        memories = await self.get_relevant_memories(user_id, prompt)
        if not memories:
            return ""

        memory_lines = "\n".join(f"- [{memory.id}] {memory.caption}" for memory in memories)
        return (
            "______ Notice ______\n"
            "This is not part of what the user has prompted. The app the user uses "
            "here has a memory feature enabled so that the user can mention things "
            "where the app would normally not have sufficient context, but due to "
            "the memory this app wants the mechanism to able to automatically "
            "reference things from past sessions/chats, so this is what we identified "
            "to be potentially relevant from past chat:\n"
            "<memory-references>\n"
            f"{memory_lines}\n"
            "</memory-references>\n"
            "____________________\n\n"
            f"{prompt}"
        )

    async def extract_memories(self, user_id: str, conversation: list[dict[str, str]]) -> None:
        """Extract and save memories from conversation (fire-and-forget)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{self._base_url}/memories/extract",
                    json={"user_id": user_id, "conversation": conversation},
                )
            logger.info(
                "memory_extraction_sent",
                user_id=user_id,
                message_count=len(conversation),
            )
        except Exception as exc:
            logger.warning("memory_extraction_failed", user_id=user_id, error=str(exc))


@lru_cache
def get_memory_service() -> MemoryService:
    """Get cached memory service instance."""
    settings = get_settings()
    return MemoryService(
        base_url=settings.memory_service_url,
        timeout=settings.memory_timeout_seconds,
    )
