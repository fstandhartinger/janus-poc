"""Web search API endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from janus_gateway.services.web_search import web_search

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    num_results: int = Field(
        default=10,
        validation_alias=AliasChoices("num_results", "max_results"),
    )


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchResponse(BaseModel):
    query: str
    source: str
    results: List[SearchResult]


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@router.post("/web", response_model=List[SearchResult])
async def web_search_endpoint(request: SearchRequest) -> List[SearchResult]:
    """Perform web search using configured providers."""
    try:
        _, results = await web_search(request.query, request.num_results)
    except Exception as exc:  # noqa: BLE001 - surface upstream errors cleanly
        raise _http_error(exc) from exc
    return [SearchResult(**item) for item in results]


@router.post("", response_model=SearchResponse)
async def web_search_compat(request: SearchRequest) -> SearchResponse:
    """Compatibility endpoint mirroring chutes-search response shape."""
    try:
        source, results = await web_search(request.query, request.num_results)
    except Exception as exc:  # noqa: BLE001 - surface upstream errors cleanly
        raise _http_error(exc) from exc
    return SearchResponse(
        query=request.query,
        source=source,
        results=[SearchResult(**item) for item in results],
    )
