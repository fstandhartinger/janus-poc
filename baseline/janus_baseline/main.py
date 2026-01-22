"""Janus Baseline Competitor - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Union

import structlog
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from janus_baseline import __version__
from janus_baseline.config import Settings, get_settings
from janus_baseline.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from janus_baseline.services import (
    ComplexityDetector,
    LLMService,
    SandyService,
    get_complexity_detector,
    get_llm_service,
    get_sandy_service,
)

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


async def stream_response(
    request: ChatCompletionRequest,
    complexity_detector: ComplexityDetector,
    llm_service: LLMService,
    sandy_service: SandyService,
) -> AsyncGenerator[str, None]:
    """Generate streaming response based on complexity."""
    is_complex, reason = complexity_detector.is_complex(request.messages)

    logger.info(
        "chat_completion_request",
        model=request.model,
        stream=True,
        is_complex=is_complex,
        complexity_reason=reason,
        message_count=len(request.messages),
    )

    if is_complex and sandy_service.is_available:
        # Complex path with Sandy
        async for chunk in sandy_service.execute_complex(request):
            yield f"data: {chunk.model_dump_json()}\n\n"
    else:
        # Fast path with direct LLM
        async for chunk in llm_service.stream(request):
            yield f"data: {chunk.model_dump_json()}\n\n"

    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    complexity_detector: ComplexityDetector = Depends(get_complexity_detector),
    llm_service: LLMService = Depends(get_llm_service),
    sandy_service: SandyService = Depends(get_sandy_service),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """OpenAI-compatible chat completions endpoint."""

    if request.stream:
        return StreamingResponse(
            stream_response(request, complexity_detector, llm_service, sandy_service),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    else:
        # Non-streaming - always use fast path
        is_complex, reason = complexity_detector.is_complex(request.messages)
        logger.info(
            "chat_completion_request",
            model=request.model,
            stream=False,
            is_complex=is_complex,
            complexity_reason=reason,
        )
        return await llm_service.complete(request)


def main() -> None:
    """Run the baseline competitor with uvicorn."""
    import uvicorn

    uvicorn.run(
        "janus_baseline.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
