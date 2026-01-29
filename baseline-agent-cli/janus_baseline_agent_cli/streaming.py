"""Streaming helpers for baseline-agent-cli."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import time
from typing import AsyncGenerator, Callable


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
    last_yield = time.perf_counter()

    async for chunk in llm_response:
        buffer += chunk
        now = time.perf_counter()
        time_since_last = (now - last_yield) * 1000

        if len(buffer) >= min_chunk_size or time_since_last >= max_buffer_time_ms:
            yield buffer
            buffer = ""
            last_yield = now

    if buffer:
        yield buffer


async def stream_with_keepalive(
    llm_response: AsyncGenerator[str, None],
    *,
    keepalive_interval: float,
    keepalive_factory: Callable[[], str],
    on_chunk: Callable[[str], None] | None = None,
) -> AsyncGenerator[str, None]:
    if keepalive_interval <= 0:
        async for chunk in llm_response:
            if on_chunk:
                on_chunk(chunk)
            yield chunk
        return

    stream_iter = llm_response.__aiter__()
    pending = asyncio.create_task(stream_iter.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=keepalive_interval)
            if pending in done:
                try:
                    chunk = pending.result()
                except StopAsyncIteration:
                    break
                if on_chunk:
                    on_chunk(chunk)
                yield chunk
                pending = asyncio.create_task(stream_iter.__anext__())
            else:
                yield keepalive_factory()
    finally:
        if not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
