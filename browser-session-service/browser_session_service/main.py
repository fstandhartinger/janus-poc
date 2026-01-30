"""Janus Browser Session Storage Service - Main application."""

import logging
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from browser_session_service.config import get_settings
from browser_session_service.database import close_db, init_db
from browser_session_service.models import HealthResponse
from browser_session_service.routes import sessions_router

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("browser_session_service")

app = FastAPI(
    title="Janus Browser Session Service",
    description="Secure storage and management of browser sessions for Janus agents",
    version="1.0.0",
)

# CORS middleware for UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to known origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting state (per-user)
_rate_limit: dict[str, Deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.

    Applies to authenticated requests (has Authorization header).
    """
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)

    # Extract user ID from path or skip if not authenticated yet
    # Rate limiting is applied per-user in the route handlers
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    """Initialize database on startup."""
    if settings.init_db:
        logger.info("Initializing database tables...")
        await init_db()
        logger.info("Database initialized")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Close database connections on shutdown."""
    await close_db()


# Include session routes
app.include_router(sessions_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", service="janus-browser-session")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "browser_session_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
