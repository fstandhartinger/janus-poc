"""Chat completions endpoint with OpenAI compatibility and streaming."""

import asyncio
import contextlib
import time
import uuid
from typing import AsyncGenerator, Union, cast

import httpx
import structlog
from fastapi import APIRouter, Depends, Request, Response
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
from janus_gateway.services import CompetitorRegistry, MessageProcessor, get_competitor_registry
from janus_gateway.services.debug_registry import DebugRequestRegistry, get_debug_registry

router = APIRouter(prefix="/v1", tags=["chat"])
logger = structlog.get_logger()
message_processor = MessageProcessor()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def generate_debug_request_id() -> str:
    """Generate a unique debug request ID."""
    return f"debug-{uuid.uuid4().hex[:16]}"


async def stream_from_competitor(
    client: httpx.AsyncClient,
    competitor_url: str,
    request: ChatCompletionRequest,
    request_id: str,
    settings: Settings,
    debug_request_id: str | None = None,
    baseline_agent: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream responses from a competitor, adding keep-alives."""
    keep_alive_interval = settings.keep_alive_interval
    done_sent = False

    # Prepare request for competitor (exclude janus-specific fields)
    competitor_request = request.model_dump(
        exclude_none=True,
        exclude={"competitor_id"},
    )

    try:
        headers: dict[str, str] = {}
        if debug_request_id:
            headers["X-Debug-Request-Id"] = debug_request_id
        if baseline_agent:
            headers["X-Baseline-Agent"] = baseline_agent
        async with client.stream(
            "POST",
            f"{competitor_url}/v1/chat/completions",
            json=competitor_request,
            timeout=settings.request_timeout,
            headers=headers or None,
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                try:
                    error_text = error_body.decode("utf-8", errors="replace")
                except Exception:
                    error_text = "<binary data>"
                logger.error(
                    "competitor_error",
                    status_code=response.status_code,
                    body=error_text,
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

            line_queue: asyncio.Queue[object] = asyncio.Queue()
            done_sentinel = object()

            async def read_lines() -> None:
                try:
                    async for line in response.aiter_lines():
                        await line_queue.put(line)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await line_queue.put(exc)
                finally:
                    await line_queue.put(done_sentinel)

            reader_task = asyncio.create_task(read_lines())
            try:
                while True:
                    try:
                        item = await asyncio.wait_for(
                            line_queue.get(), timeout=keep_alive_interval
                        )
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
                        continue

                    if item is done_sentinel:
                        break
                    if isinstance(item, Exception):
                        raise item

                    line = cast(str, item)
                    if line.startswith("data:") or line.startswith(":"):
                        yield f"{line}\n\n"
                        if line.startswith("data:") and line[5:].strip() == "[DONE]":
                            done_sent = True
                            break
            finally:
                if not reader_task.done():
                    reader_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await reader_task

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
        return
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
        return

    if not done_sent:
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
    response: Response,
    registry: CompetitorRegistry = Depends(get_competitor_registry),
    debug_registry: DebugRequestRegistry = Depends(get_debug_registry),
    settings: Settings = Depends(get_settings),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""
    request_id = generate_request_id()
    debug_request_id = generate_debug_request_id() if request.debug else None
    baseline_agent = http_request.headers.get("X-Baseline-Agent")
    start_time = time.time()

    logger.info(
        "chat_completion_request",
        request_id=request_id,
        model=request.model,
        stream=request.stream,
        competitor_id=request.competitor_id,
        message_count=len(request.messages),
    )

    processed_messages = [
        message_processor.process_message(message) for message in request.messages
    ]
    processed_request = request.model_copy(update={"messages": processed_messages})

    # Resolve competitor: explicit competitor_id overrides model-based selection.
    competitor = registry.get(request.competitor_id) if request.competitor_id else None
    default_competitor = registry.get_default()
    if competitor is None and request.competitor_id is None:
        competitor = registry.get(request.model) or default_competitor

    if debug_request_id:
        baseline_id = competitor.id if competitor else (default_competitor.id if default_competitor else "")
        if baseline_id:
            debug_registry.register(debug_request_id, baseline_id)
        if not request.stream:
            response.headers["X-Debug-Request-Id"] = debug_request_id

    if request.stream:
        # Streaming response
        if competitor:
            async def stream_with_logging() -> AsyncGenerator[str, None]:
                async with httpx.AsyncClient() as client:
                    async for chunk in stream_from_competitor(
                        client,
                        competitor.url,
                        processed_request,
                        request_id,
                        settings,
                        debug_request_id,
                        baseline_agent,
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
                    **({"X-Debug-Request-Id": debug_request_id} if debug_request_id else {}),
                },
            )
        else:
            # Mock response for development
            async def mock_with_logging() -> AsyncGenerator[str, None]:
                async for chunk in mock_streaming_response(processed_request, request_id, settings):
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
                    **({"X-Debug-Request-Id": debug_request_id} if debug_request_id else {}),
                },
            )

    else:
        # Non-streaming response
        if competitor:
            async with httpx.AsyncClient() as client:
                try:
                    fwd_headers: dict[str, str] = {}
                    if debug_request_id:
                        fwd_headers["X-Debug-Request-Id"] = debug_request_id
                    if baseline_agent:
                        fwd_headers["X-Baseline-Agent"] = baseline_agent
                    competitor_response = await client.post(
                        f"{competitor.url}/v1/chat/completions",
                        json=processed_request.model_dump(
                            exclude_none=True,
                            exclude={"competitor_id"},
                        ),
                        timeout=settings.request_timeout,
                        headers=fwd_headers or None,
                    )
                    competitor_response.raise_for_status()
                    data = competitor_response.json()
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
