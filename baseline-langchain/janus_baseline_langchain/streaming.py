"""Streaming helpers for baseline-langchain."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator


async def optimized_stream_response(
    llm_response: AsyncGenerator[str, None],
    *,
    min_chunk_size: int = 10,
    max_buffer_time_ms: float = 50,
) -> AsyncGenerator[str, None]:
    """
    Optimize streaming by batching small chunks and keeping cadence consistent.
    """
    buffer = ""
    last_yield = asyncio.get_event_loop().time()

    async for chunk in llm_response:
        buffer += chunk
        now = asyncio.get_event_loop().time()
        time_since_last = (now - last_yield) * 1000

        if len(buffer) >= min_chunk_size or time_since_last >= max_buffer_time_ms:
            yield buffer
            buffer = ""
            last_yield = now

    if buffer:
        yield buffer
