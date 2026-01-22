"""Health check endpoint."""

from fastapi import APIRouter

from janus_gateway import __version__
from janus_gateway.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
    )
