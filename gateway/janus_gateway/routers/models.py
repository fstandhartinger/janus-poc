"""Models endpoint for OpenAI compatibility."""

from fastapi import APIRouter, Depends

from janus_gateway.models import ModelInfo, ModelsResponse
from janus_gateway.services import CompetitorRegistry, get_competitor_registry

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    registry: CompetitorRegistry = Depends(get_competitor_registry),
) -> ModelsResponse:
    """List available models (competitors)."""
    competitors = registry.list_all(enabled_only=True)
    models = [
        ModelInfo(
            id=c.id,
            owned_by="janus" if c.is_baseline else "competitor",
        )
        for c in competitors
    ]
    return ModelsResponse(data=models)
