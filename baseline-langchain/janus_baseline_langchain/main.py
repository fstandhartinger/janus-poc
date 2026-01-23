"""Janus Baseline LangChain - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Iterable, Union

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel

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
    ImageUrlContent,
    Message,
    MessageContent,
    MessageRole,
    TextContent,
    Usage,
)

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
    return f"data: {chunk.model_dump_json()}\n\n"


def _tool_event_message(event: dict[str, Any]) -> str:
    tool_name = event.get("name") or event.get("data", {}).get("name") or "tool"
    return tool_name


async def stream_agent_response(
    agent: Any,
    request_id: str,
    model: str,
    user_input: str,
    history: Iterable[object],
    include_usage: bool,
) -> AsyncGenerator[str, None]:
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
                yield _chunk_payload(
                    request_id,
                    model,
                    Delta(reasoning_content=f"Running tool: {tool_name}..."),
                )
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


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""
    request_id = _generate_request_id()
    model = request.model or settings.model

    chat_history = [
        msg
        for msg in (
            _to_langchain_message(m) for m in request.messages[:-1]
        )
        if msg is not None
    ]
    user_input = _extract_text(request.messages[-1].content)

    logger.info(
        "chat_completion_request",
        request_id=request_id,
        model=model,
        stream=request.stream,
        message_count=len(request.messages),
    )

    agent = create_agent(settings)

    if request.stream:
        include_usage = bool(request.stream_options and request.stream_options.include_usage)
        return StreamingResponse(
            stream_agent_response(
                agent,
                request_id,
                model,
                user_input,
                chat_history,
                include_usage,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    try:
        result = await agent.ainvoke(
            {"input": user_input, "chat_history": chat_history}
        )
        output = str(result.get("output", ""))
    except Exception as exc:
        logger.error("agent_invoke_error", error=str(exc))
        output = "Error: failed to generate response."

    return _format_response(request_id, model, output)


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
