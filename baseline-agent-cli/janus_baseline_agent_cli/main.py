"""Janus Baseline Competitor - FastAPI application entry point."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Union

import structlog
from fastapi import Depends, FastAPI, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from janus_baseline_agent_cli import __version__
from janus_baseline_agent_cli.config import get_settings
from janus_baseline_agent_cli.models import (
    ChatCompletionRequest,
    ChatCompletionChunk,
    ChatCompletionResponse,
    GenerationFlags,
    ImageUrlContent,
    Message,
    MessageRole,
    TextContent,
    ToolDefinition,
    extract_text_content,
)
from janus_baseline_agent_cli.models.debug import DebugEventType
from janus_baseline_agent_cli.services import (
    ComplexityDetector,
    LLMService,
    MemoryService,
    SandyService,
    get_complexity_detector,
    get_llm_service,
    get_memory_service,
    get_sandy_service,
)
from janus_baseline_agent_cli.services.debug import DebugEmitter
from janus_baseline_agent_cli.streaming import optimized_stream_response
from janus_baseline_agent_cli.tools.memory import INVESTIGATE_MEMORY_TOOL
from janus_baseline_agent_cli.router.debug import router as debug_router
from janus_baseline_agent_cli.router.server import app as router_app

settings = get_settings()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def _latest_user_message_index(messages: list[Message]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == MessageRole.USER:
            return index
    return None


def _extract_last_user_prompt(messages: list[Message]) -> str:
    index = _latest_user_message_index(messages)
    if index is None:
        return ""
    return extract_text_content(messages[index].content)


def _build_conversation_base(messages: list[Message]) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    for message in messages:
        conversation.append(
            {
                "role": message.role.value,
                "content": extract_text_content(message.content),
            }
        )
    return conversation


def _extract_chunk_content(chunk: ChatCompletionChunk) -> str:
    if not chunk.choices:
        return ""
    parts: list[str] = []
    for choice in chunk.choices:
        if choice.delta and choice.delta.content:
            parts.append(choice.delta.content)
    return "".join(parts)


def _extract_response_content(response: ChatCompletionResponse) -> str:
    if not response.choices:
        return ""
    message = response.choices[0].message
    content = getattr(message, "content", None)
    return content or ""


def _tool_name(tool: object) -> str | None:
    if isinstance(tool, dict):
        function = tool.get("function")
        if isinstance(function, dict):
            return function.get("name")
        return None
    function = getattr(tool, "function", None)
    if function is None:
        return None
    if isinstance(function, dict):
        return function.get("name")
    return getattr(function, "name", None)


def _apply_memory_tool(request: ChatCompletionRequest, enable: bool) -> None:
    if not request.tools and not enable:
        request.tools = None
        return

    filtered: list[object] = []
    for tool in request.tools or []:
        if _tool_name(tool) != "investigate_memory":
            filtered.append(tool)

    if enable:
        filtered.append(ToolDefinition(**INVESTIGATE_MEMORY_TOOL))

    request.tools = filtered or None


def _inject_memory_context(messages: list[Message], memory_context: str) -> None:
    index = _latest_user_message_index(messages)
    if index is None or not memory_context:
        return
    message = messages[index]
    content = message.content

    if isinstance(content, list):
        image_parts: list[object] = []
        for part in content:
            if isinstance(part, ImageUrlContent):
                image_parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "image_url":
                image_parts.append(part)
        message.content = [TextContent(text=memory_context), *image_parts]
        return

    message.content = memory_context


def _extract_auth_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    token = authorization.strip()
    if not token:
        return None
    parts = token.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return token


def _generation_flags_payload(flags: GenerationFlags | None) -> dict[str, bool] | None:
    if not flags:
        return None
    payload = flags.model_dump()
    if any(payload.values()):
        return payload
    return None


def _resolve_debug_request_id(header_value: str | None, enabled: bool) -> str | None:
    if not enabled:
        return None
    if header_value:
        return header_value
    return f"debug-{uuid.uuid4().hex[:16]}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(
        "baseline_starting",
        version=__version__,
        host=settings.host,
        port=settings.port,
    )
    yield
    logger.info("baseline_stopping")


app = FastAPI(
    title="Janus Baseline Competitor",
    description="Reference implementation for the Janus competitive network",
    version=__version__,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Cannot use credentials with wildcard origin per CORS spec
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debug_router)

# Mount the model router at /router for agent path access
# Sandy agents can use https://<host>/router/v1/chat/completions
app.mount("/router", router_app)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


async def stream_response(
    request: ChatCompletionRequest,
    complexity_detector: ComplexityDetector,
    llm_service: LLMService,
    sandy_service: SandyService,
    memory_service: MemoryService | None = None,
    memory_user_id: str | None = None,
    conversation_base: list[dict[str, str]] | None = None,
    debug_emitter: DebugEmitter | None = None,
) -> AsyncGenerator[str, None]:
    """Generate streaming response based on complexity."""
    if debug_emitter:
        await debug_emitter.emit(
            DebugEventType.COMPLEXITY_CHECK_START,
            "DETECT",
            "Starting complexity analysis",
        )
    analysis = await complexity_detector.analyze_async(
        request.messages,
        request.generation_flags,
    )
    is_complex = analysis.is_complex
    reason = analysis.reason
    using_agent = settings.always_use_agent or (is_complex and sandy_service.is_available)
    flags_payload = _generation_flags_payload(request.generation_flags)
    metadata_payload = (
        {
            "generation_flags": flags_payload,
            "using_agent": using_agent,
            "complexity_reason": reason,
        }
        if flags_payload
        else None
    )

    if debug_emitter:
        if analysis.keywords_matched:
            await debug_emitter.emit(
                DebugEventType.COMPLEXITY_CHECK_KEYWORD,
                "KEYWORDS",
                f"Keyword match: {', '.join(analysis.keywords_matched)}",
                data={"keywords": analysis.keywords_matched},
            )
        if analysis.reason.startswith("llm_verification"):
            await debug_emitter.emit(
                DebugEventType.COMPLEXITY_CHECK_LLM,
                "LLM_VERIFY",
                f"LLM verification: {analysis.reason}",
                data={"reason": analysis.reason},
            )
        await debug_emitter.emit(
            DebugEventType.COMPLEXITY_CHECK_COMPLETE,
            "DETECT",
            f"Complexity: {'complex' if analysis.is_complex else 'simple'}",
            data={"is_complex": analysis.is_complex, "reason": analysis.reason},
        )
        await debug_emitter.emit(
            DebugEventType.AGENT_PATH_START if using_agent else DebugEventType.FAST_PATH_START,
            "SANDY" if using_agent else "FAST_LLM",
            "Routing to agent path" if using_agent else "Routing to fast path",
            data={"using_agent": using_agent, "reason": analysis.reason},
        )

    logger.info(
        "complexity_check",
        is_complex=is_complex,
        reason=reason,
        keywords_matched=analysis.keywords_matched,
        multimodal_detected=analysis.multimodal_detected,
        has_images=analysis.has_images,
        image_count=analysis.image_count,
        sandy_available=sandy_service.is_available,
        text_preview=analysis.text_preview,
        always_use_agent=settings.always_use_agent,
    )

    logger.info(
        "chat_completion_request",
        model=request.model,
        stream=True,
        is_complex=is_complex,
        complexity_reason=reason,
        message_count=len(request.messages),
    )

    full_response_parts: list[str] = []

    async def raw_stream() -> AsyncGenerator[str, None]:
        first_chunk = True
        fast_path_emitted = False
        try:
            if using_agent:
                # Use Sandy's agent/run API if enabled (faster, better configured)
                if settings.use_sandy_agent_api:
                    async for chunk in sandy_service.execute_via_agent_api(
                        request,
                        debug_emitter=debug_emitter,
                    ):
                        chunk_text = _extract_chunk_content(chunk)
                        if chunk_text:
                            full_response_parts.append(chunk_text)
                        if first_chunk and metadata_payload:
                            chunk = chunk.model_copy(update={"metadata": metadata_payload})
                        first_chunk = False
                        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
                else:
                    # Fallback to manual exec approach
                    async for chunk in sandy_service.execute_complex(
                        request,
                        debug_emitter=debug_emitter,
                    ):
                        chunk_text = _extract_chunk_content(chunk)
                        if chunk_text:
                            full_response_parts.append(chunk_text)
                        if first_chunk and metadata_payload:
                            chunk = chunk.model_copy(update={"metadata": metadata_payload})
                        first_chunk = False
                        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
            else:
                async for chunk in llm_service.stream(request):
                    if debug_emitter and not fast_path_emitted:
                        await debug_emitter.emit(
                            DebugEventType.FAST_PATH_STREAM,
                            "FAST_LLM",
                            "Streaming fast-path response",
                        )
                        fast_path_emitted = True
                    chunk_text = _extract_chunk_content(chunk)
                    if chunk_text:
                        full_response_parts.append(chunk_text)
                    if first_chunk and metadata_payload:
                        chunk = chunk.model_copy(update={"metadata": metadata_payload})
                    first_chunk = False
                    yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.RESPONSE_COMPLETE,
                    "SSE",
                    "Response complete",
                )
            yield "data: [DONE]\n\n"
        finally:
            if memory_service and memory_user_id and conversation_base is not None:
                assistant_response = "".join(full_response_parts)
                conversation = conversation_base + [
                    {"role": "assistant", "content": assistant_response}
                ]
                asyncio.create_task(
                    memory_service.extract_memories(
                        user_id=memory_user_id,
                        conversation=conversation,
                    )
                )

    async for payload in optimized_stream_response(raw_stream()):
        yield payload


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    response: Response,
    complexity_detector: ComplexityDetector = Depends(get_complexity_detector),
    llm_service: LLMService = Depends(get_llm_service),
    sandy_service: SandyService = Depends(get_sandy_service),
    memory_service: MemoryService = Depends(get_memory_service),
    authorization: str | None = Header(default=None, alias="Authorization"),
    debug_request_id_header: str | None = Header(default=None, alias="X-Debug-Request-Id"),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""

    auth_token = _extract_auth_token(authorization)
    if auth_token:
        request._auth_token = auth_token

    debug_enabled = bool(request.debug)
    debug_request_id = _resolve_debug_request_id(debug_request_id_header, debug_enabled)
    debug_emitter = DebugEmitter(debug_request_id, debug_enabled)

    if debug_request_id and not request.stream:
        response.headers["X-Debug-Request-Id"] = debug_request_id

    if debug_emitter:
        await debug_emitter.emit(
            DebugEventType.REQUEST_RECEIVED,
            "REQ",
            "Request received",
            data={
                "model": request.model,
                "message_count": len(request.messages),
                "debug": debug_enabled,
            },
        )

    memory_enabled = bool(
        settings.enable_memory_feature and request.enable_memory and request.user_id
    )
    conversation_base = _build_conversation_base(request.messages)
    has_memory_context = False
    if memory_enabled and request.user_id:
        prompt = _extract_last_user_prompt(request.messages)
        memory_context = await memory_service.get_memory_context(request.user_id, prompt)
        if memory_context:
            has_memory_context = True
            messages_for_processing = [
                message.model_copy(deep=True) for message in request.messages
            ]
            _inject_memory_context(messages_for_processing, memory_context)
            request.messages = messages_for_processing

    _apply_memory_tool(request, enable=bool(memory_enabled and has_memory_context))

    if request.stream:
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if debug_request_id:
            headers["X-Debug-Request-Id"] = debug_request_id
        return StreamingResponse(
            stream_response(
                request,
                complexity_detector,
                llm_service,
                sandy_service,
                memory_service if memory_enabled else None,
                request.user_id if memory_enabled else None,
                conversation_base if memory_enabled else None,
                debug_emitter,
            ),
            media_type="text/event-stream",
            headers=headers,
        )
    else:
        # Non-streaming - route based on complexity
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.COMPLEXITY_CHECK_START,
                "DETECT",
                "Starting complexity analysis",
            )
        analysis = complexity_detector.analyze(
            request.messages,
            request.generation_flags,
        )
        is_complex = analysis.is_complex
        reason = analysis.reason
        logger.info(
            "complexity_check",
            is_complex=is_complex,
            reason=reason,
            keywords_matched=analysis.keywords_matched,
            multimodal_detected=analysis.multimodal_detected,
            has_images=analysis.has_images,
            image_count=analysis.image_count,
            sandy_available=sandy_service.is_available,
            text_preview=analysis.text_preview,
            always_use_agent=settings.always_use_agent,
        )
        logger.info(
            "chat_completion_request",
            model=request.model,
            stream=False,
            is_complex=is_complex,
            complexity_reason=reason,
        )
        if debug_emitter:
            if analysis.keywords_matched:
                await debug_emitter.emit(
                    DebugEventType.COMPLEXITY_CHECK_KEYWORD,
                    "KEYWORDS",
                    f"Keyword match: {', '.join(analysis.keywords_matched)}",
                    data={"keywords": analysis.keywords_matched},
                )
            if analysis.reason.startswith("llm_verification"):
                await debug_emitter.emit(
                    DebugEventType.COMPLEXITY_CHECK_LLM,
                    "LLM_VERIFY",
                    f"LLM verification: {analysis.reason}",
                    data={"reason": analysis.reason},
                )
            await debug_emitter.emit(
                DebugEventType.COMPLEXITY_CHECK_COMPLETE,
                "DETECT",
                f"Complexity: {'complex' if analysis.is_complex else 'simple'}",
                data={"is_complex": analysis.is_complex, "reason": analysis.reason},
            )
            await debug_emitter.emit(
                DebugEventType.AGENT_PATH_START if is_complex else DebugEventType.FAST_PATH_START,
                "SANDY" if is_complex else "FAST_LLM",
                "Routing to agent path" if is_complex else "Routing to fast path",
                data={"using_agent": is_complex, "reason": analysis.reason},
            )
        if settings.always_use_agent or (is_complex and sandy_service.is_available):
            # Use Sandy's agent/run API if enabled (faster, better configured)
            if settings.use_sandy_agent_api:
                response = await sandy_service.complete_via_agent_api(
                    request,
                    debug_emitter=debug_emitter,
                )
            else:
                response = await sandy_service.complete(
                    request,
                    debug_emitter=debug_emitter,
                )
        else:
            response = await llm_service.complete(request)

        if memory_enabled and request.user_id:
            assistant_response = _extract_response_content(response)
            conversation = conversation_base + [
                {"role": "assistant", "content": assistant_response}
            ]
            asyncio.create_task(
                memory_service.extract_memories(
                    user_id=request.user_id,
                    conversation=conversation,
                )
            )

        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.RESPONSE_COMPLETE,
                "SSE",
                "Response complete",
            )

        return response


def main() -> None:
    """Run the baseline competitor with uvicorn."""
    import uvicorn

    uvicorn.run(
        "janus_baseline_agent_cli.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
