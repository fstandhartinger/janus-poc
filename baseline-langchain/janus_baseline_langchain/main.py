"""Janus Baseline LangChain - FastAPI application entry point."""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
import json
import re
from typing import Any, AsyncGenerator, Iterable, Union

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr
from starlette.middleware.base import BaseHTTPMiddleware

from janus_baseline_langchain import __version__
from janus_baseline_langchain.agent import create_agent
from janus_baseline_langchain.config import Settings, get_settings
from janus_baseline_langchain.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChunkChoice,
    Delta,
    FinishReason,
    FunctionCall,
    Artifact,
    GenerationFlags,
    ImageUrlContent,
    Message,
    MessageContent,
    MessageRole,
    TextContent,
    ToolCall,
    Usage,
)
from janus_baseline_langchain.models.debug import DebugEventType
from janus_baseline_langchain.streaming import optimized_stream_response
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.router.debug import router as debug_router
from janus_baseline_langchain.services import (
    MemoryService,
    clear_artifact_collection,
    get_artifact_manager,
    get_collected_artifacts,
    get_complexity_detector,
    get_memory_service,
    set_request_auth_token,
    start_artifact_collection,
    ComplexityDetector,
)
from janus_baseline_langchain.services.debug import DebugEmitter
from janus_baseline_langchain.services.vision import (
    contains_images,
    convert_to_langchain_messages,
    create_vision_chain,
)

# Global router instance for metrics tracking
_router_instance: CompositeRoutingChatModel | None = None

settings = get_settings()

# Correlation ID context variable for request tracing
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID from context."""
    return correlation_id_var.get() or ""


# Configure structured logging with contextvars for correlation
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if not settings.debug
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to extract correlation ID from headers and bind to context."""

    async def dispatch(self, request: Request, call_next):
        # Get or create correlation ID
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or f"corr-{uuid.uuid4().hex[:16]}"
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Set correlation ID in context var
        correlation_id_var.set(correlation_id)

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            logger.info("request_received")
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_complete",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
            correlation_id_var.set("")


def _split_stream_content(content: str, max_chars: int = 40) -> list[str]:
    if len(content) <= max_chars:
        return [content]
    return [content[i : i + max_chars] for i in range(0, len(content), max_chars)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(
        "baseline_langchain_starting",
        version=__version__,
        host=settings.host,
        port=settings.port,
    )
    yield
    logger.info("baseline_langchain_stopping")


app = FastAPI(
    title="Janus Baseline LangChain",
    description="LangChain-based baseline competitor implementation",
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

# Add correlation ID middleware for request tracing
app.add_middleware(CorrelationMiddleware)

app.include_router(debug_router)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/artifacts/{artifact_name}")
async def get_artifact(
    artifact_name: str,
    artifact_manager=Depends(get_artifact_manager),
) -> FileResponse:
    """Serve locally generated artifacts."""
    try:
        path = artifact_manager.resolve_path(artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)


@app.get("/v1/router/metrics")
async def get_router_metrics() -> dict[str, Any]:
    """Get composite model router metrics."""
    global _router_instance
    if _router_instance is None:
        return {
            "enabled": settings.use_model_router,
            "error": "Router not initialized or not enabled",
        }
    return {
        "enabled": True,
        **_router_instance.get_metrics(),
    }


def _extract_text(content: MessageContent | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for part in content:
        if isinstance(part, TextContent):
            parts.append(part.text)
        elif isinstance(part, ImageUrlContent):
            parts.append(f"[Image: {part.image_url.url}]")
    return " ".join(p for p in parts if p).strip()


def _latest_user_message_index(messages: list[Message]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == MessageRole.USER:
            return index
    return None


def _build_conversation_base(messages: list[Message]) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    for message in messages:
        conversation.append(
            {
                "role": message.role.value,
                "content": _extract_text(message.content),
            }
        )
    return conversation


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


def _to_langchain_message(message: Message) -> object | None:
    content = _extract_text(message.content)
    if message.role == MessageRole.USER:
        return HumanMessage(content=content)
    if message.role == MessageRole.ASSISTANT:
        return AIMessage(content=content)
    if message.role == MessageRole.SYSTEM:
        return SystemMessage(content=content)
    if message.role == MessageRole.TOOL:
        return ToolMessage(content=content, tool_call_id=message.tool_call_id or "tool")
    return None


def _generate_request_id() -> str:
    import uuid

    return f"chatcmpl-baseline-langchain-{uuid.uuid4().hex[:12]}"


def _resolve_debug_request_id(header_value: str | None, enabled: bool) -> str | None:
    if not enabled:
        return None
    if header_value:
        return header_value
    import uuid

    return f"debug-{uuid.uuid4().hex[:16]}"


def _format_response(
    request_id: str,
    model: str,
    output: str,
    artifacts: list[Artifact] | None = None,
) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id=request_id,
        model=model,
        choices=[
            Choice(
                message=Message(
                    role=MessageRole.ASSISTANT,
                    content=output,
                    artifacts=artifacts or None,
                ),
                finish_reason=FinishReason.STOP,
            )
        ],
    )


def _format_tool_call_response(
    request_id: str,
    model: str,
    tool_call: ToolCall,
) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id=request_id,
        model=model,
        choices=[
            Choice(
                message=Message(
                    role=MessageRole.ASSISTANT,
                    content=None,
                    tool_calls=[tool_call],
                ),
                finish_reason=FinishReason.TOOL_CALLS,
            )
        ],
    )


def _chunk_payload(
    request_id: str,
    model: str,
    delta: Delta,
    finish_reason: FinishReason | None = None,
    usage: Usage | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    chunk = ChatCompletionChunk(
        id=request_id,
        model=model,
        choices=[ChunkChoice(delta=delta, finish_reason=finish_reason)],
        usage=usage,
        metadata=metadata,
    )
    return f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"


def _tool_event_message(event: dict[str, Any]) -> str:
    tool_name = event.get("name") or event.get("data", {}).get("name") or "tool"
    return tool_name


def _debug_step_for_tool(tool_name: str) -> str:
    normalized = tool_name.lower()
    if "search" in normalized:
        return "TOOL_SEARCH"
    if "image" in normalized or "vision" in normalized:
        return "TOOL_IMG"
    if "file" in normalized or "read" in normalized or "write" in normalized:
        return "TOOL_FILES"
    if "code" in normalized or "exec" in normalized or "python" in normalized:
        return "TOOL_CODE"
    return "TOOL_CODE"


def _get_router(
    settings: Settings,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> CompositeRoutingChatModel:
    """Get or create the global router instance."""
    if api_key_override or base_url_override:
        return CompositeRoutingChatModel(
            api_key=api_key_override or settings.openai_api_key or "dummy-key",
            base_url=base_url_override or settings.openai_base_url,
            default_temperature=settings.temperature,
        )
    global _router_instance
    if _router_instance is None:
        api_key = settings.chutes_api_key or settings.openai_api_key or "dummy-key"
        _router_instance = CompositeRoutingChatModel(
            api_key=api_key,
            base_url=settings.openai_base_url,
            default_temperature=settings.temperature,
        )
    return _router_instance


def _create_text_chain(
    settings: Settings,
    model: str,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> ChatOpenAI:
    api_key_value = api_key_override or settings.openai_api_key or "dummy-key"
    api_key = SecretStr(api_key_value)
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url_override or settings.openai_base_url,
        temperature=settings.temperature,
        streaming=True,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == MessageRole.USER:
            return _extract_text(message.content)
    return ""


def _resolve_request_auth(
    request: ChatCompletionRequest,
    settings: Settings,
) -> tuple[str | None, str]:
    token = request.chutes_access_token or getattr(request, "_auth_token", None)
    if token:
        return token, settings.chutes_api_base
    openai_base = settings.openai_base_url
    chutes_base = settings.chutes_api_base
    if (
        settings.chutes_api_key
        and openai_base.rstrip("/") == chutes_base.rstrip("/")
    ):
        return settings.chutes_api_key, chutes_base
    if settings.openai_api_key:
        return settings.openai_api_key, openai_base
    if settings.chutes_api_key:
        return settings.chutes_api_key, chutes_base
    return None, openai_base


def _generation_flags_payload(flags: GenerationFlags | None) -> dict[str, bool] | None:
    if not flags:
        return None
    payload = flags.model_dump()
    if any(payload.values()):
        return payload
    return None


def _generation_flag_reasons(flags: GenerationFlags) -> list[str]:
    reasons: list[str] = []
    if flags.generate_image:
        reasons.append("image generation requested")
    if flags.generate_video:
        reasons.append("video generation requested")
    if flags.generate_audio:
        reasons.append("audio generation requested")
    if flags.deep_research:
        reasons.append("deep research requested")
    if flags.web_search:
        reasons.append("web search requested")
    return reasons


def _build_agent_prompt(user_message: str, flags: GenerationFlags | None) -> str:
    instructions: list[str] = []

    if flags:
        if flags.generate_image:
            instructions.append(
                "The user has explicitly requested IMAGE GENERATION. "
                "You MUST generate one or more images as part of your response using the Chutes image API."
            )
        if flags.generate_video:
            instructions.append(
                "The user has explicitly requested VIDEO GENERATION. "
                "You MUST generate a video as part of your response using the Chutes video API."
            )
        if flags.generate_audio:
            instructions.append(
                "The user has explicitly requested AUDIO GENERATION. "
                "You MUST generate audio (speech/music) as part of your response using the Chutes TTS/audio API."
            )
        if flags.deep_research:
            instructions.append(
                "The user has explicitly requested DEEP RESEARCH. "
                "You MUST perform comprehensive research with citations using chutes-search max mode."
            )
        if flags.web_search:
            instructions.append(
                "The user has explicitly requested WEB SEARCH. "
                "You MUST search the internet for current information to answer this query."
            )

    if not instructions:
        return user_message

    instruction_block = "\n".join(f"- {instruction}" for instruction in instructions)

    return (
        "______ Generation Instructions ______\n"
        "The user has enabled the following generation modes:\n"
        f"{instruction_block}\n\n"
        "Please ensure your response includes the requested generated content.\n"
        "_____________________________________\n\n"
        f"{user_message}"
    )


def _build_agent_context(messages: list[Message]) -> tuple[str, list[object]]:
    last_index = _latest_user_message_index(messages)
    user_input = _latest_user_text(messages)
    history: list[object] = []
    if last_index is None:
        return user_input, history
    for message in messages[:last_index]:
        converted = _to_langchain_message(message)
        if converted:
            history.append(converted)
    return user_input, history


def _extract_first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _infer_tool_call(
    request: ChatCompletionRequest,
) -> ToolCall | None:
    if not request.tools:
        return None

    tool_names = [tool.function.name for tool in request.tools]
    prompt = _latest_user_text(request.messages)
    lowered = prompt.lower()

    selected = None
    tool_choice = request.tool_choice
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function") if tool_choice else None
        if isinstance(function, dict):
            selected = function.get("name")
    elif isinstance(tool_choice, str) and tool_choice not in {"auto", "none"}:
        selected = tool_choice

    if not selected:
        if "weather" in lowered and "get_weather" in tool_names:
            selected = "get_weather"
        elif "exchange rate" in lowered and "get_exchange_rate" in tool_names:
            selected = "get_exchange_rate"
        elif "stock" in lowered and "get_stock_price" in tool_names:
            selected = "get_stock_price"
        elif "convert" in lowered and "convert_units" in tool_names:
            selected = "convert_units"
        elif "time" in lowered and "get_time" in tool_names:
            selected = "get_time"
        elif "search" in lowered and "search" in tool_names:
            selected = "search"
        elif "search" in lowered and "web_search" in tool_names:
            selected = "web_search"
        elif any(token in lowered for token in ("calculate", "compute", "factorial")) and "calculator" in tool_names:
            selected = "calculator"
        elif any(token in lowered for token in ("code", "python", "script")) and "code_execute" in tool_names:
            selected = "code_execute"
        elif any(token in lowered for token in ("image", "picture", "photo")) and "image_generation" in tool_names:
            selected = "image_generation"

    if not selected:
        return None

    arguments: dict[str, Any] = {}
    if selected == "get_weather":
        location = _extract_first_match(r"in ([a-zA-Z\\s]+)", prompt) or "unknown"
        arguments = {"location": location}
    elif selected == "get_exchange_rate":
        match = re.findall(r"\\b[A-Z]{3}\\b", prompt)
        if len(match) >= 2:
            arguments = {"base_currency": match[0], "target_currency": match[1]}
    elif selected == "get_stock_price":
        ticker = _extract_first_match(r"\\b([A-Z]{2,5})\\b", prompt)
        if ticker:
            arguments = {"ticker": ticker}
    elif selected == "convert_units":
        value = _extract_first_match(r"(\\d+(?:\\.\\d+)?)", prompt)
        arguments = {"value": float(value) if value else 1, "from_unit": "", "to_unit": ""}
    elif selected == "get_time":
        timezone = _extract_first_match(r"in ([A-Za-z/_]+)", prompt) or "UTC"
        arguments = {"timezone": timezone}
    elif selected in {"search", "web_search"}:
        arguments = {"query": prompt}
    elif selected == "calculator":
        expression = _extract_first_match(r"([0-9\\s\\+\\-\\*\\/\\(\\)\\.]+)", prompt)
        arguments = {"expression": expression or "0"}
    elif selected == "code_execute":
        arguments = {"language": "python", "code": prompt}
    elif selected == "image_generation":
        arguments = {"prompt": prompt}

    return ToolCall(
        id="tool-0",
        function=FunctionCall(name=selected, arguments=json.dumps(arguments)),
    )


async def _stream_tool_call_response(
    request_id: str,
    model: str,
    tool_call: ToolCall,
    include_usage: bool,
    metadata: dict[str, Any] | None = None,
    debug_emitter: DebugEmitter | None = None,
) -> AsyncGenerator[str, None]:
    if debug_emitter:
        tool_name = tool_call.function.name
        await debug_emitter.emit(
            DebugEventType.TOOL_CALL_START,
            _debug_step_for_tool(tool_name),
            f"Running tool: {tool_name}",
            data={"tool": tool_name},
        )
    yield _chunk_payload(
        request_id,
        model,
        Delta(role=MessageRole.ASSISTANT),
        metadata=metadata,
    )
    yield _chunk_payload(
        request_id,
        model,
        Delta(tool_calls=[tool_call]),
        finish_reason=FinishReason.TOOL_CALLS,
    )
    if include_usage:
        yield _chunk_payload(
            request_id,
            model,
            Delta(),
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )
    yield _chunk_payload(
        request_id,
        model,
        Delta(),
        finish_reason=FinishReason.STOP,
    )
    if debug_emitter:
        tool_name = tool_call.function.name
        await debug_emitter.emit(
            DebugEventType.TOOL_CALL_COMPLETE,
            _debug_step_for_tool(tool_name),
            f"Tool finished: {tool_name}",
            data={"tool": tool_name},
        )
        await debug_emitter.emit(
            DebugEventType.RESPONSE_COMPLETE,
            "SSE",
            "Response complete",
        )
    yield "data: [DONE]\n\n"


async def _stream_basic_response(
    request_id: str,
    settings: Settings,
    messages: list[object],
    include_usage: bool,
    response_collector: list[str] | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    metadata: dict[str, Any] | None = None,
    debug_emitter: DebugEmitter | None = None,
) -> AsyncGenerator[str, None]:
    use_router = settings.use_model_router and not api_key_override
    if use_router:
        llm = _get_router(
            settings,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        model_name = "composite-routing"
    else:
        llm = _create_text_chain(
            settings,
            settings.model,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        model_name = settings.model

    started = False
    metadata_sent = False

    async for chunk in llm.astream(messages):
        content = getattr(chunk, "content", None)
        if not content:
            continue
        content_parts = _split_stream_content(str(content))
        if not started:
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.FAST_PATH_STREAM,
                    "FAST_LLM",
                    "Streaming fast-path response",
                    data={"model": model_name},
                )
            yield _chunk_payload(
                request_id,
                model_name,
                Delta(role=MessageRole.ASSISTANT),
                metadata=metadata if not metadata_sent else None,
            )
            started = True
            metadata_sent = True
        for part in content_parts:
            if response_collector is not None:
                response_collector.append(part)
            yield _chunk_payload(
                request_id,
                model_name,
                Delta(content=part),
            )

    if not started:
        yield _chunk_payload(
            request_id,
            model_name,
            Delta(role=MessageRole.ASSISTANT),
            metadata=metadata if not metadata_sent else None,
        )
        metadata_sent = True

    if include_usage:
        yield _chunk_payload(
            request_id,
            model_name,
            Delta(),
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    yield _chunk_payload(
        request_id,
        model_name,
        Delta(),
        finish_reason=FinishReason.STOP,
    )
    if debug_emitter:
        await debug_emitter.emit(
            DebugEventType.RESPONSE_COMPLETE,
            "SSE",
            "Response complete",
        )
    yield "data: [DONE]\n\n"


async def _run_basic_completion(
    settings: Settings,
    messages: list[object],
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> tuple[str, str]:
    use_router = settings.use_model_router and not api_key_override
    if use_router:
        llm = _get_router(
            settings,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        result = await llm.ainvoke(messages)
        return "composite-routing", str(getattr(result, "content", result))

    llm = _create_text_chain(
        settings,
        settings.model,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
    )
    result = await llm.ainvoke(messages)
    return settings.model, str(getattr(result, "content", result))


async def stream_agent_response(
    agent: Any,
    request_id: str,
    model: str,
    user_input: str,
    history: Iterable[object],
    include_usage: bool,
    response_collector: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    debug_emitter: DebugEmitter | None = None,
) -> AsyncGenerator[str, None]:
    async def raw_stream() -> AsyncGenerator[str, None]:
        tool_index = 0
        agent_stream_started = False
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.AGENT_THINKING,
                "AGENT",
                "Starting agent execution",
            )
        yield _chunk_payload(
            request_id,
            model,
            Delta(role=MessageRole.ASSISTANT),
            metadata=metadata,
        )

        try:
            async for event in agent.astream_events(
                {"input": user_input, "chat_history": list(history)},
                version="v2",
            ):
                event_type = event.get("event")
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    content = getattr(chunk, "content", None)
                    if content:
                        if debug_emitter and not agent_stream_started:
                            await debug_emitter.emit(
                                DebugEventType.RESPONSE_CHUNK,
                                "AGENT",
                                "Streaming agent response",
                            )
                            agent_stream_started = True
                        if response_collector is not None:
                            response_collector.append(str(content))
                        yield _chunk_payload(
                            request_id,
                            model,
                            Delta(content=content),
                        )
                elif event_type == "on_tool_start":
                    tool_name = _tool_event_message(event)
                    tool_payload = event.get("data", {})
                    tool_input = tool_payload.get("input") or tool_payload.get("inputs") or {}
                    if not isinstance(tool_input, dict):
                        tool_input = {"input": tool_input}
                    tool_call = ToolCall(
                        id=f"tool-{tool_index}",
                        function=FunctionCall(
                            name=tool_name,
                            arguments=json.dumps(tool_input),
                        ),
                    )
                    if debug_emitter:
                        await debug_emitter.emit(
                            DebugEventType.TOOL_CALL_START,
                            _debug_step_for_tool(tool_name),
                            f"Running tool: {tool_name}",
                            data={"tool": tool_name},
                        )
                    yield _chunk_payload(
                        request_id,
                        model,
                        Delta(
                            reasoning_content=f"Running tool: {tool_name}...",
                            tool_calls=[tool_call],
                        ),
                    )
                    tool_index += 1
                elif event_type == "on_tool_end":
                    tool_name = _tool_event_message(event)
                    if debug_emitter:
                        await debug_emitter.emit(
                            DebugEventType.TOOL_CALL_COMPLETE,
                            _debug_step_for_tool(tool_name),
                            f"Tool finished: {tool_name}",
                            data={"tool": tool_name},
                        )
                    yield _chunk_payload(
                        request_id,
                        model,
                        Delta(reasoning_content=f"Tool finished: {tool_name}."),
                    )
                elif event_type == "on_chain_error":
                    if debug_emitter:
                        await debug_emitter.emit(
                            DebugEventType.ERROR,
                            "AGENT",
                            "Agent chain failed",
                        )
                    yield _chunk_payload(
                        request_id,
                        model,
                        Delta(content="Error: agent chain failed."),
                        finish_reason=FinishReason.STOP,
                    )
                    yield "data: [DONE]\n\n"
                    return
        except Exception as exc:
            logger.error("agent_stream_error", error=str(exc))
            if debug_emitter:
                await debug_emitter.emit(
                    DebugEventType.ERROR,
                    "AGENT",
                    f"Agent stream error: {exc}",
                )
            yield _chunk_payload(
                request_id,
                model,
                Delta(content="Error: failed to stream response."),
                finish_reason=FinishReason.STOP,
            )
            yield "data: [DONE]\n\n"
            return

        artifacts = get_collected_artifacts()
        if artifacts:
            if debug_emitter:
                for artifact in artifacts:
                    await debug_emitter.emit(
                        DebugEventType.FILE_CREATED,
                        "TOOL_FILES",
                        f"Artifact created: {artifact.display_name}",
                        data={
                            "filename": artifact.display_name,
                            "artifact_id": artifact.id,
                        },
                    )
            yield _chunk_payload(
                request_id,
                model,
                Delta(
                    janus={
                        "event": "artifacts",
                        "payload": {
                            "artifacts": [
                                artifact.model_dump(mode="json") for artifact in artifacts
                            ]
                        },
                    }
                ),
            )

        if include_usage:
            yield _chunk_payload(
                request_id,
                model,
                Delta(),
                usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

        yield _chunk_payload(
            request_id,
            model,
            Delta(),
            finish_reason=FinishReason.STOP,
        )
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.RESPONSE_COMPLETE,
                "SSE",
                "Response complete",
            )
        yield "data: [DONE]\n\n"

    async for payload in optimized_stream_response(raw_stream()):
        yield payload


async def _stream_vision_response(
    request_id: str,
    settings: Settings,
    messages: list[object],
    include_usage: bool,
    response_collector: list[str] | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
    metadata: dict[str, Any] | None = None,
    debug_emitter: DebugEmitter | None = None,
) -> AsyncGenerator[str, None]:
    async def raw_stream() -> AsyncGenerator[str, None]:
        primary = settings.vision_model_primary
        fallback = settings.vision_model_fallback

        for attempt_model in (primary, fallback):
            try:
                llm = create_vision_chain(
                    settings,
                    attempt_model,
                    api_key_override=api_key_override,
                    base_url_override=base_url_override,
                )
                started = False
                metadata_sent = False

                async for chunk in llm.astream(messages):
                    content = getattr(chunk, "content", None)
                    if not content:
                        continue
                    content_parts = _split_stream_content(str(content))
                    if not started:
                        if debug_emitter:
                            await debug_emitter.emit(
                                DebugEventType.FAST_PATH_STREAM,
                                "FAST_LLM",
                                "Streaming vision response",
                                data={"model": attempt_model},
                            )
                        yield _chunk_payload(
                            request_id,
                            attempt_model,
                            Delta(role=MessageRole.ASSISTANT),
                            metadata=metadata if not metadata_sent else None,
                        )
                        yield _chunk_payload(
                            request_id,
                            attempt_model,
                            Delta(reasoning_content="Processing request..."),
                        )
                        started = True
                        metadata_sent = True
                    for part in content_parts:
                        if response_collector is not None:
                            response_collector.append(part)
                        yield _chunk_payload(
                            request_id,
                            attempt_model,
                            Delta(content=part),
                        )

                if not started:
                    yield _chunk_payload(
                        request_id,
                        attempt_model,
                        Delta(role=MessageRole.ASSISTANT),
                        metadata=metadata if not metadata_sent else None,
                    )
                    metadata_sent = True

                if include_usage:
                    yield _chunk_payload(
                        request_id,
                        attempt_model,
                        Delta(),
                        usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                    )

                yield _chunk_payload(
                    request_id,
                    attempt_model,
                    Delta(),
                    finish_reason=FinishReason.STOP,
                )
                if debug_emitter:
                    await debug_emitter.emit(
                        DebugEventType.RESPONSE_COMPLETE,
                        "SSE",
                        "Response complete",
                    )
                yield "data: [DONE]\n\n"
                return
            except Exception as exc:
                if attempt_model == primary:
                    logger.warning(
                        "vision_stream_primary_failed",
                        error=str(exc),
                        fallback=fallback,
                    )
                    continue
                logger.error("vision_stream_error", error=str(exc))
                yield _chunk_payload(
                    request_id,
                    attempt_model,
                    Delta(content="Error: failed to stream vision response."),
                    finish_reason=FinishReason.STOP,
                )
                yield "data: [DONE]\n\n"
                return

    async for payload in optimized_stream_response(raw_stream()):
        yield payload


async def _run_vision_completion(
    settings: Settings,
    messages: list[object],
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> tuple[str, str]:
    primary = settings.vision_model_primary
    fallback = settings.vision_model_fallback

    try:
        llm = create_vision_chain(
            settings,
            primary,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        result = await llm.ainvoke(messages)
        return primary, str(getattr(result, "content", result))
    except Exception as exc:
        logger.warning("vision_primary_failed", error=str(exc), fallback=fallback)
        llm = create_vision_chain(
            settings,
            fallback,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        result = await llm.ainvoke(messages)
        return fallback, str(getattr(result, "content", result))


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    complexity_detector: ComplexityDetector = Depends(get_complexity_detector),
    memory_service: MemoryService = Depends(get_memory_service),
    authorization: str | None = Header(default=None, alias="Authorization"),
    debug_request_id_header: str | None = Header(default=None, alias="X-Debug-Request-Id"),
    correlation_id_header: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""
    request_id = _generate_request_id()

    # Get correlation ID from header or context
    correlation_id = correlation_id_header or get_correlation_id()

    auth_token = _extract_auth_token(authorization) or request.chutes_access_token
    if auth_token:
        request._auth_token = auth_token
    set_request_auth_token(auth_token)
    start_artifact_collection()
    api_key_override, base_url_override = _resolve_request_auth(request, settings)

    debug_enabled = bool(request.debug)
    debug_request_id = _resolve_debug_request_id(debug_request_id_header, debug_enabled)
    debug_emitter = DebugEmitter(debug_request_id, debug_enabled, correlation_id)

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
        prompt = _latest_user_text(request.messages)
        memory_context = await memory_service.get_memory_context(request.user_id, prompt)
        if memory_context:
            has_memory_context = True
            messages_for_processing = [
                message.model_copy(deep=True) for message in request.messages
            ]
            _inject_memory_context(messages_for_processing, memory_context)
            request.messages = messages_for_processing

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

    flags_payload = _generation_flags_payload(request.generation_flags)
    use_generation_agent = analysis.is_complex
    flag_reasons = (
        _generation_flag_reasons(request.generation_flags)
        if request.generation_flags and flags_payload
        else []
    )
    metadata_payload = None
    if flags_payload or use_generation_agent:
        metadata_payload = {
            "generation_flags": flags_payload,
            "using_agent": use_generation_agent,
            "complexity_reason": analysis.reason,
        }

    logger.info(
        "complexity_check",
        request_id=request_id,
        is_complex=analysis.is_complex,
        reason=analysis.reason,
        keywords_matched=analysis.keywords_matched,
        multimodal_detected=analysis.multimodal_detected,
        has_images=analysis.has_images,
        image_count=analysis.image_count,
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
            DebugEventType.AGENT_PATH_START if use_generation_agent else DebugEventType.FAST_PATH_START,
            "SANDY" if use_generation_agent else "FAST_LLM",
            "Routing to agent path" if use_generation_agent else "Routing to fast path",
            data={"using_agent": use_generation_agent, "reason": analysis.reason},
        )

    use_vision = settings.enable_vision_routing and contains_images(request.messages)
    model = settings.vision_model_primary if use_vision else (request.model or settings.model)

    logger.info(
        "chat_completion_request",
        request_id=request_id,
        model=model,
        stream=request.stream,
        message_count=len(request.messages),
        vision_routing=use_vision,
    )

    tool_call = None if use_generation_agent else _infer_tool_call(request)

    if request.stream:
        full_response_parts: list[str] = []
        response_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if debug_request_id:
            response_headers["X-Debug-Request-Id"] = debug_request_id

        async def stream_with_memory(
            stream: AsyncGenerator[str, None],
        ) -> AsyncGenerator[str, None]:
            try:
                async for payload in stream:
                    yield payload
            finally:
                if memory_enabled and request.user_id:
                    assistant_response = "".join(full_response_parts)
                    conversation = conversation_base + [
                        {"role": "assistant", "content": assistant_response}
                    ]
                    asyncio.create_task(
                        memory_service.extract_memories(
                            user_id=request.user_id,
                            conversation=conversation,
                        )
                    )
                clear_artifact_collection()

        include_usage = bool(request.stream_options and request.stream_options.include_usage)
        if use_generation_agent:
            user_input, history = _build_agent_context(request.messages)
            agent_prompt = _build_agent_prompt(user_input, request.generation_flags)
            agent = create_agent(
                settings,
                user_id=request.user_id,
                enable_memory=memory_enabled,
                has_memory_context=has_memory_context,
                api_key_override=api_key_override,
                base_url_override=base_url_override,
            )
            stream = stream_agent_response(
                agent,
                request_id,
                request.model or settings.model,
                agent_prompt,
                history,
                include_usage,
                response_collector=full_response_parts,
                metadata=metadata_payload,
                debug_emitter=debug_emitter,
            )
            wrapped_stream = stream_with_memory(optimized_stream_response(stream))
            return StreamingResponse(
                wrapped_stream,
                media_type="text/event-stream",
                headers=response_headers,
            )
        if tool_call and not use_vision:
            stream = _stream_tool_call_response(
                request_id,
                model,
                tool_call,
                include_usage,
                metadata=metadata_payload,
                debug_emitter=debug_emitter,
            )
            wrapped_stream = stream_with_memory(optimized_stream_response(stream))
            return StreamingResponse(
                wrapped_stream,
                media_type="text/event-stream",
                headers=response_headers,
            )
        if use_vision:
            vision_messages = convert_to_langchain_messages(request.messages)
            stream = _stream_vision_response(
                request_id,
                settings,
                vision_messages,
                include_usage,
                response_collector=full_response_parts,
                api_key_override=api_key_override,
                base_url_override=base_url_override,
                metadata=metadata_payload,
                debug_emitter=debug_emitter,
            )
            wrapped_stream = stream_with_memory(optimized_stream_response(stream))
            return StreamingResponse(
                wrapped_stream,
                media_type="text/event-stream",
                headers=response_headers,
            )
        base_messages = convert_to_langchain_messages(request.messages)
        stream = _stream_basic_response(
            request_id,
            settings,
            base_messages,
            include_usage,
            response_collector=full_response_parts,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
            metadata=metadata_payload,
            debug_emitter=debug_emitter,
        )
        wrapped_stream = stream_with_memory(optimized_stream_response(stream))
        return StreamingResponse(
            wrapped_stream,
            media_type="text/event-stream",
            headers=response_headers,
        )

    if use_generation_agent:
        user_input, history = _build_agent_context(request.messages)
        agent_prompt = _build_agent_prompt(user_input, request.generation_flags)
        agent = create_agent(
            settings,
            user_id=request.user_id,
            enable_memory=memory_enabled,
            has_memory_context=has_memory_context,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
        try:
            result = await agent.ainvoke(
                {"input": agent_prompt, "chat_history": list(history)}
            )
            if isinstance(result, dict):
                output = str(result.get("output") or result)
            else:
                output = str(result)
        except Exception as exc:
            logger.error("agent_invoke_error", error=str(exc))
            output = "Error: failed to generate response."
        artifacts = get_collected_artifacts()
        response = _format_response(
            request_id,
            request.model or settings.model,
            output,
            artifacts=artifacts or None,
        )
        if debug_emitter and artifacts:
            for artifact in artifacts:
                await debug_emitter.emit(
                    DebugEventType.FILE_CREATED,
                    "TOOL_FILES",
                    f"Artifact created: {artifact.display_name}",
                    data={
                        "filename": artifact.display_name,
                        "artifact_id": artifact.id,
                    },
                )
        if memory_enabled and request.user_id:
            conversation = conversation_base + [
                {"role": "assistant", "content": output}
            ]
            asyncio.create_task(
                memory_service.extract_memories(
                    user_id=request.user_id,
                    conversation=conversation,
                )
            )
        clear_artifact_collection()
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.RESPONSE_COMPLETE,
                "SSE",
                "Response complete",
            )
        return response

    if tool_call and not use_vision:
        response = _format_tool_call_response(request_id, model, tool_call)
        if memory_enabled and request.user_id:
            conversation = conversation_base + [
                {"role": "assistant", "content": ""}
            ]
            asyncio.create_task(
                memory_service.extract_memories(
                    user_id=request.user_id,
                    conversation=conversation,
                )
            )
        clear_artifact_collection()
        if debug_emitter:
            tool_name = tool_call.function.name
            await debug_emitter.emit(
                DebugEventType.TOOL_CALL_START,
                _debug_step_for_tool(tool_name),
                f"Running tool: {tool_name}",
                data={"tool": tool_name},
            )
            await debug_emitter.emit(
                DebugEventType.TOOL_CALL_COMPLETE,
                _debug_step_for_tool(tool_name),
                f"Tool finished: {tool_name}",
                data={"tool": tool_name},
            )
            await debug_emitter.emit(
                DebugEventType.RESPONSE_COMPLETE,
                "SSE",
                "Response complete",
            )
        return response

    if use_vision:
        vision_messages = convert_to_langchain_messages(request.messages)
        try:
            model_name, output = await _run_vision_completion(
                settings,
                vision_messages,
                api_key_override=api_key_override,
                base_url_override=base_url_override,
            )
        except Exception as exc:
            logger.error("vision_completion_error", error=str(exc))
            output = "Error: failed to generate vision response."
            model_name = model
        response = _format_response(request_id, model_name, output)
        if memory_enabled and request.user_id:
            conversation = conversation_base + [
                {"role": "assistant", "content": output}
            ]
            asyncio.create_task(
                memory_service.extract_memories(
                    user_id=request.user_id,
                    conversation=conversation,
                )
            )
        clear_artifact_collection()
        if debug_emitter:
            await debug_emitter.emit(
                DebugEventType.RESPONSE_COMPLETE,
                "SSE",
                "Response complete",
            )
        return response

    try:
        base_messages = convert_to_langchain_messages(request.messages)
        model_name, output = await _run_basic_completion(
            settings,
            base_messages,
            api_key_override=api_key_override,
            base_url_override=base_url_override,
        )
    except Exception as exc:
        logger.error("agent_invoke_error", error=str(exc))
        output = "Error: failed to generate response."
        model_name = model

    response = _format_response(request_id, model_name, output)
    if memory_enabled and request.user_id:
        conversation = conversation_base + [
            {"role": "assistant", "content": output}
        ]
        asyncio.create_task(
            memory_service.extract_memories(
                user_id=request.user_id,
                conversation=conversation,
            )
        )
    clear_artifact_collection()
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
        "janus_baseline_langchain.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
