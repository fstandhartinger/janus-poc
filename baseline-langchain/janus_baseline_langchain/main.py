"""Janus Baseline LangChain - FastAPI application entry point."""

from contextlib import asynccontextmanager
import json
import re
from typing import Any, AsyncGenerator, Iterable, Union

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pydantic.v1 import SecretStr

from janus_baseline_langchain import __version__
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
    ImageUrlContent,
    Message,
    MessageContent,
    MessageRole,
    TextContent,
    ToolCall,
    Usage,
)
from janus_baseline_langchain.streaming import optimized_stream_response
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.services.vision import (
    contains_images,
    convert_to_langchain_messages,
    create_vision_chain,
)

# Global router instance for metrics tracking
_router_instance: CompositeRoutingChatModel | None = None

settings = get_settings()

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


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


def _format_response(request_id: str, model: str, output: str) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id=request_id,
        model=model,
        choices=[
            Choice(
                message=Message(role=MessageRole.ASSISTANT, content=output),
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
) -> str:
    chunk = ChatCompletionChunk(
        id=request_id,
        model=model,
        choices=[ChunkChoice(delta=delta, finish_reason=finish_reason)],
        usage=usage,
    )
    return f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"


def _tool_event_message(event: dict[str, Any]) -> str:
    tool_name = event.get("name") or event.get("data", {}).get("name") or "tool"
    return tool_name


def _get_router(settings: Settings) -> CompositeRoutingChatModel:
    """Get or create the global router instance."""
    global _router_instance
    if _router_instance is None:
        api_key = settings.chutes_api_key or settings.openai_api_key or "dummy-key"
        _router_instance = CompositeRoutingChatModel(
            api_key=api_key,
            base_url=settings.openai_base_url,
            default_temperature=settings.temperature,
        )
    return _router_instance


def _create_text_chain(settings: Settings, model: str) -> ChatOpenAI:
    api_key = (
        SecretStr(settings.openai_api_key)
        if settings.openai_api_key
        else SecretStr("dummy-key")
    )
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=settings.openai_base_url,
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
) -> AsyncGenerator[str, None]:
    yield _chunk_payload(
        request_id,
        model,
        Delta(role=MessageRole.ASSISTANT),
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
    yield "data: [DONE]\n\n"


async def _stream_basic_response(
    request_id: str,
    settings: Settings,
    messages: list[object],
    include_usage: bool,
) -> AsyncGenerator[str, None]:
    if settings.use_model_router:
        llm = _get_router(settings)
        model_name = "composite-routing"
    else:
        llm = _create_text_chain(settings, settings.model)
        model_name = settings.model

    started = False

    async for chunk in llm.astream(messages):
        content = getattr(chunk, "content", None)
        if not content:
            continue
        content_parts = _split_stream_content(str(content))
        if not started:
            yield _chunk_payload(
                request_id,
                model_name,
                Delta(role=MessageRole.ASSISTANT),
            )
            started = True
        for part in content_parts:
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
        )

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
    yield "data: [DONE]\n\n"


async def _run_basic_completion(
    settings: Settings,
    messages: list[object],
) -> tuple[str, str]:
    if settings.use_model_router:
        llm = _get_router(settings)
        result = await llm.ainvoke(messages)
        return "composite-routing", str(getattr(result, "content", result))

    llm = _create_text_chain(settings, settings.model)
    result = await llm.ainvoke(messages)
    return settings.model, str(getattr(result, "content", result))


async def stream_agent_response(
    agent: Any,
    request_id: str,
    model: str,
    user_input: str,
    history: Iterable[object],
    include_usage: bool,
) -> AsyncGenerator[str, None]:
    async def raw_stream() -> AsyncGenerator[str, None]:
        tool_index = 0
        yield _chunk_payload(
            request_id,
            model,
            Delta(role=MessageRole.ASSISTANT),
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
                    yield _chunk_payload(
                        request_id,
                        model,
                        Delta(reasoning_content=f"Tool finished: {tool_name}."),
                    )
                elif event_type == "on_chain_error":
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
            yield _chunk_payload(
                request_id,
                model,
                Delta(content="Error: failed to stream response."),
                finish_reason=FinishReason.STOP,
            )
            yield "data: [DONE]\n\n"
            return

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
        yield "data: [DONE]\n\n"

    async for payload in optimized_stream_response(raw_stream()):
        yield payload


async def _stream_vision_response(
    request_id: str,
    settings: Settings,
    messages: list[object],
    include_usage: bool,
) -> AsyncGenerator[str, None]:
    async def raw_stream() -> AsyncGenerator[str, None]:
        primary = settings.vision_model_primary
        fallback = settings.vision_model_fallback

        for attempt_model in (primary, fallback):
            try:
                llm = create_vision_chain(settings, attempt_model)
                started = False

                async for chunk in llm.astream(messages):
                    content = getattr(chunk, "content", None)
                    if not content:
                        continue
                    content_parts = _split_stream_content(str(content))
                    if not started:
                        yield _chunk_payload(
                            request_id,
                            attempt_model,
                            Delta(role=MessageRole.ASSISTANT),
                        )
                        yield _chunk_payload(
                            request_id,
                            attempt_model,
                            Delta(reasoning_content="Processing request..."),
                        )
                        started = True
                    for part in content_parts:
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
                    )

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
) -> tuple[str, str]:
    primary = settings.vision_model_primary
    fallback = settings.vision_model_fallback

    try:
        llm = create_vision_chain(settings, primary)
        result = await llm.ainvoke(messages)
        return primary, str(getattr(result, "content", result))
    except Exception as exc:
        logger.warning("vision_primary_failed", error=str(exc), fallback=fallback)
        llm = create_vision_chain(settings, fallback)
        result = await llm.ainvoke(messages)
        return fallback, str(getattr(result, "content", result))


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""
    request_id = _generate_request_id()
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

    tool_call = _infer_tool_call(request)

    if request.stream:
        include_usage = bool(request.stream_options and request.stream_options.include_usage)
        if tool_call and not use_vision:
            return StreamingResponse(
                _stream_tool_call_response(request_id, model, tool_call, include_usage),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        if use_vision:
            vision_messages = convert_to_langchain_messages(request.messages)
            return StreamingResponse(
                _stream_vision_response(
                    request_id,
                    settings,
                    vision_messages,
                    include_usage,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        base_messages = convert_to_langchain_messages(request.messages)
        return StreamingResponse(
            _stream_basic_response(
                request_id,
                settings,
                base_messages,
                include_usage,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                },
            )

    if tool_call and not use_vision:
        return _format_tool_call_response(request_id, model, tool_call)

    if use_vision:
        vision_messages = convert_to_langchain_messages(request.messages)
        try:
            model_name, output = await _run_vision_completion(settings, vision_messages)
        except Exception as exc:
            logger.error("vision_completion_error", error=str(exc))
            output = "Error: failed to generate vision response."
            model_name = model
        return _format_response(request_id, model_name, output)

    try:
        base_messages = convert_to_langchain_messages(request.messages)
        model_name, output = await _run_basic_completion(settings, base_messages)
    except Exception as exc:
        logger.error("agent_invoke_error", error=str(exc))
        output = "Error: failed to generate response."

    return _format_response(request_id, model_name, output)


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
