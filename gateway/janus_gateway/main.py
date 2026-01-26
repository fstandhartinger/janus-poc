"""Janus Gateway - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from janus_gateway import __version__
from janus_gateway.config import get_settings
from janus_gateway.middleware.logging import RequestLoggingMiddleware
from janus_gateway.middleware.pre_release_password import PreReleasePasswordMiddleware
from janus_gateway.routers import (
    artifacts_router,
    chat_router,
    debug_router,
    health_router,
    logs_router,
    memories_router,
    models_router,
    transcription_router,
    research_router,
    tts_router,
)

settings = get_settings()

# Configure structured logging
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
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def log_service_health_status() -> None:
    """Log health status of configured services on startup."""
    # Check transcription service
    if not settings.chutes_api_key:
        logger.warning(
            "transcription_not_configured",
            message=(
                "CHUTES_API_KEY not configured - transcription endpoint will return 503. "
                "Set CHUTES_API_KEY environment variable to enable voice transcription."
            ),
        )
    else:
        logger.info("transcription_service_configured")

    # Check gateway URL
    if not settings.gateway_url:
        logger.warning(
            "gateway_url_not_configured",
            message="GATEWAY_URL not set - some features may not work correctly.",
        )

    # Log competitor configuration
    logger.info(
        "competitor_config",
        default_competitor=settings.default_competitor,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info(
        "gateway_starting",
        version=__version__,
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
    )
    log_service_health_status()
    yield
    # Shutdown
    logger.info("gateway_stopping")


# Create FastAPI app
app = FastAPI(
    title="Janus Gateway API",
    description="""
OpenAI-compatible AI agent gateway for the Janus competitive network.

## Features
- Chat completions with streaming support
- Multimodal inputs (text, images)
- Artifact generation (images, files, data)
- Generative UI responses
- Memory and personalization
- Intelligent agent routing

## Authentication
Currently open access. API keys coming soon.
""".strip(),
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Pre-release password middleware
if settings.pre_release_password:
    app.add_middleware(PreReleasePasswordMiddleware, password=settings.pre_release_password)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(artifacts_router)
app.include_router(debug_router)
app.include_router(logs_router)
app.include_router(transcription_router)
app.include_router(research_router)
app.include_router(tts_router)
app.include_router(memories_router)


def main() -> None:
    """Run the gateway with uvicorn."""
    import uvicorn

    uvicorn.run(
        "janus_gateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
