"""Chat completions endpoint with OpenAI compatibility and streaming."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Union

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from janus_gateway.config import Settings, get_settings
from janus_gateway.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChunkChoice,
    Delta,
    FinishReason,
    Message,
    MessageRole,
    Usage,
)
from janus_gateway.services import CompetitorRegistry, get_competitor_registry

router = APIRouter(prefix="/v1", tags=["chat"])
logger = structlog.get_logger()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


async def stream_from_competitor(
    client: httpx.AsyncClient,
    competitor_url: str,
    request: ChatCompletionRequest,
    request_id: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Stream responses from a competitor, adding keep-alives."""
    last_event_time = time.time()
    keep_alive_interval = settings.keep_alive_interval

    # Prepare request for competitor (exclude janus-specific fields)
    competitor_request = request.model_dump(
        exclude_none=True,
        exclude={"competitor_id"},
    )

    try:
        async with client.stream(
            "POST",
            f"{competitor_url}/v1/chat/completions",
            json=competitor_request,
            timeout=settings.request_timeout,
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                logger.error(
                    "competitor_error",
                    status_code=response.status_code,
                    body=error_body.decode(),
                )
                # Yield error as SSE
                error_chunk = ChatCompletionChunk(
                    id=request_id,
                    model=request.model,
                    choices=[
                        ChunkChoice(
                            delta=Delta(content=f"Error from competitor: {response.status_code}"),
                            finish_reason=FinishReason.STOP,
                        )
                    ],
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return

            async for line in response.aiter_lines():
                current_time = time.time()

                # Emit keep-alive if needed
                while current_time - last_event_time > keep_alive_interval:
                    yield ": ping\n\n"
                    last_event_time += keep_alive_interval

                if line.startswith("data:"):
                    yield f"{line}\n\n"
                    last_event_time = current_time
                elif line.startswith(":"):
                    # Pass through comments/keep-alives
                    yield f"{line}\n\n"
                    last_event_time = current_time

    except httpx.TimeoutException:
        logger.error("competitor_timeout", url=competitor_url)
        error_chunk = ChatCompletionChunk(
            id=request_id,
            model=request.model,
            choices=[
                ChunkChoice(
                    delta=Delta(content="Request timed out"),
                    finish_reason=FinishReason.STOP,
                )
            ],
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    except httpx.RequestError as e:
        logger.error("competitor_request_error", error=str(e))
        error_chunk = ChatCompletionChunk(
            id=request_id,
            model=request.model,
            choices=[
                ChunkChoice(
                    delta=Delta(content=f"Connection error: {e}"),
                    finish_reason=FinishReason.STOP,
                )
            ],
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"


async def mock_streaming_response(
    request: ChatCompletionRequest,
    request_id: str,
    settings: Settings,
) -> AsyncGenerator[str, None]:
    """Generate a mock streaming response for development/testing."""
    model = request.model

    # Emit initial role
    initial_chunk = ChatCompletionChunk(
        id=request_id,
        model=model,
        choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"

    # Emit some reasoning content
    reasoning_texts = [
        "Analyzing the request... ",
        "Processing your query... ",
        "Generating response... ",
    ]
    for text in reasoning_texts:
        chunk = ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(reasoning_content=text))],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        await asyncio.sleep(0.1)

    # Emit content tokens
    response_text = "Hello! I'm the Janus Gateway responding to your request. This is a mock response for development purposes."
    words = response_text.split()
    for word in words:
        chunk = ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[ChunkChoice(delta=Delta(content=word + " "))],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        await asyncio.sleep(0.05)

    # Emit final chunk with finish reason
    final_chunk = ChatCompletionChunk(
        id=request_id,
        model=model,
        choices=[ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"

    # Include usage if requested
    if request.stream_options and request.stream_options.include_usage:
        usage_chunk = ChatCompletionChunk(
            id=request_id,
            model=model,
            choices=[],
            usage=Usage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        )
        yield f"data: {usage_chunk.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    registry: CompetitorRegistry = Depends(get_competitor_registry),
    settings: Settings = Depends(get_settings),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""
    request_id = generate_request_id()
    start_time = time.time()

    logger.info(
        "chat_completion_request",
        request_id=request_id,
        model=request.model,
        stream=request.stream,
        competitor_id=request.competitor_id,
        message_count=len(request.messages),
    )

    # Resolve competitor
    competitor = registry.resolve(request.competitor_id)

    if request.stream:
        # Streaming response
        if competitor:
            async def stream_with_logging() -> AsyncGenerator[str, None]:
                async with httpx.AsyncClient() as client:
                    async for chunk in stream_from_competitor(
                        client, competitor.url, request, request_id, settings
                    ):
                        yield chunk
                logger.info(
                    "chat_completion_complete",
                    request_id=request_id,
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            return StreamingResponse(
                stream_with_logging(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-Id": request_id,
                },
            )
        else:
            # Mock response for development
            async def mock_with_logging() -> AsyncGenerator[str, None]:
                async for chunk in mock_streaming_response(request, request_id, settings):
                    yield chunk
                logger.info(
                    "chat_completion_complete",
                    request_id=request_id,
                    duration_ms=int((time.time() - start_time) * 1000),
                    mock=True,
                )

            return StreamingResponse(
                mock_with_logging(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-Id": request_id,
                },
            )

    else:
        # Non-streaming response
        if competitor:
            async with httpx.AsyncClient() as client:
                try:
                    competitor_request = request.model_dump(
                        exclude_none=True,
                        exclude={"competitor_id"},
                    )
                    response = await client.post(
                        f"{competitor.url}/v1/chat/completions",
                        json=competitor_request,
                        timeout=settings.request_timeout,
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Override the ID
                    data["id"] = request_id
                    return ChatCompletionResponse(**data)
                except httpx.RequestError as e:
                    logger.warning(
                        "competitor_unavailable_fallback_mock",
                        error=str(e),
                        competitor_id=competitor.id,
                    )
                    # Fall through to mock response

        # Mock non-streaming response (no competitor or competitor unavailable)
        # Note: use_mock is always True here since competitor success returns early
        return ChatCompletionResponse(
            id=request_id,
            model=request.model,
            choices=[
                Choice(
                    message=Message(
                        role=MessageRole.ASSISTANT,
                        content="Hello! I'm the Janus Gateway. This is a mock response.",
                    ),
                    finish_reason=FinishReason.STOP,
                )
            ],
            usage=Usage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
        )
