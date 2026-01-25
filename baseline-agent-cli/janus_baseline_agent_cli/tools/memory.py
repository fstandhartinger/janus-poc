"""Memory investigation tool for the baseline agent CLI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field


class InvestigateMemoryInput(BaseModel):
    """Schema for memory investigation requests."""

    memory_ids: list[str] = Field(description="List of memory IDs to retrieve")
    query: str | None = Field(
        default=None,
        description="Optional: What you're looking for in these memories",
    )


async def _fetch_full_memories(
    memory_service_url: str,
    user_id: str,
    memory_ids: list[str],
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    if not memory_ids:
        return []

    base_url = memory_service_url.rstrip("/")
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.get(
            f"{base_url}/memories/full",
            params={
                "user_id": user_id,
                "ids": ",".join(memory_ids),
            },
        )
        response.raise_for_status()
        payload = response.json()

    memories = payload.get("memories", [])
    return memories if isinstance(memories, list) else []


def _format_memories(memories: list[dict[str, Any]], query: str | None) -> str:
    if not memories:
        return "No memories found with the provided IDs."

    formatted = ["## Retrieved Memories\n"]
    for memory in memories:
        memory_id = memory.get("id", "unknown")
        caption = memory.get("caption", "Untitled memory")
        created_at = memory.get("created_at", "unknown")
        full_text = memory.get("full_text", "")
        formatted.append(f"### [{memory_id}] {caption}")
        formatted.append(f"**Created:** {created_at}")
        formatted.append(f"\n{full_text}\n")

    if query:
        formatted.insert(0, f"*Investigating: {query}*\n")

    return "\n".join(formatted)


async def investigate_memory(
    memory_ids: list[str],
    user_id: str,
    memory_service_url: str,
    query: str | None = None,
    timeout_seconds: float = 10.0,
) -> str:
    """Retrieve full memory content for investigation."""
    try:
        memories = await _fetch_full_memories(
            memory_service_url=memory_service_url,
            user_id=user_id,
            memory_ids=memory_ids,
            timeout_seconds=timeout_seconds,
        )
        return _format_memories(memories, query)
    except Exception as exc:
        return f"Error retrieving memories: {exc}"


async def create_memory_research_folder(
    user_id: str,
    memory_ids: list[str],
    memory_service_url: str,
    timeout_seconds: float = 10.0,
) -> str:
    """Save full memories to a temporary folder for research."""
    memories = await _fetch_full_memories(
        memory_service_url=memory_service_url,
        user_id=user_id,
        memory_ids=memory_ids,
        timeout_seconds=timeout_seconds,
    )

    temp_dir = tempfile.mkdtemp(prefix="janus_memories_")
    memories_path = Path(temp_dir)

    for memory in memories:
        memory_id = memory.get("id", "unknown")
        caption = memory.get("caption", "Untitled memory")
        created_at = memory.get("created_at", "unknown")
        full_text = memory.get("full_text", "")
        mem_file = memories_path / f"{memory_id}.md"
        mem_file.write_text(
            (
                f"# {caption}\n\n"
                f"**ID:** {memory_id}\n"
                f"**Created:** {created_at}\n\n"
                "## Full Content\n\n"
                f"{full_text}"
            ),
            encoding="utf-8",
        )

    index_file = memories_path / "INDEX.md"
    index_lines = ["# Memory Index\n"]
    for memory in memories:
        memory_id = memory.get("id", "unknown")
        caption = memory.get("caption", "Untitled memory")
        index_lines.append(f"- [{memory_id}]({memory_id}.md): {caption}")
    index_file.write_text("\n".join(index_lines), encoding="utf-8")

    return str(memories_path)


INVESTIGATE_MEMORY_TOOL = {
    "type": "function",
    "function": {
        "name": "investigate_memory",
        "description": (
            "Retrieve full content of specific memories for deeper investigation. "
            "Use this when the memory captions in the notice section aren't providing "
            "enough context and you need to understand the full details. Memory IDs "
            "are shown in square brackets in the memory references section."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of memory IDs (e.g., 'mem_abc123')",
                },
                "query": {
                    "type": "string",
                    "description": "What specific information you're looking for",
                },
            },
            "required": ["memory_ids"],
        },
    },
}
