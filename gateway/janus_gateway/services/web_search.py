"""Web search helpers for the Janus gateway."""

from __future__ import annotations

from typing import Any

import httpx

from janus_gateway.config import get_settings

_SERPER_URL = "https://google.serper.dev/search"


def normalize_serper_results(payload: Any) -> list[dict[str, str]]:
    """Normalize Serper API payloads into title/url/snippet entries."""
    if not isinstance(payload, dict):
        return []
    organic = payload.get("organic")
    if not isinstance(organic, list):
        return []
    results: list[dict[str, str]] = []
    for item in organic:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("link") or item.get("url") or "")
        snippet = str(item.get("snippet") or item.get("description") or "")
        if not (title or url or snippet):
            continue
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


def normalize_searxng_results(payload: Any) -> list[dict[str, str]]:
    """Normalize SearXNG payloads into title/url/snippet entries."""
    if not isinstance(payload, dict):
        return []
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return []
    results: list[dict[str, str]] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        snippet = str(item.get("content") or item.get("snippet") or "")
        if not (title or url or snippet):
            continue
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _resolve_searxng_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/search"):
        return base
    return f"{base}/search"


async def serper_search(query: str, num_results: int = 10) -> list[dict[str, str]]:
    """Execute web search via Serper API."""
    settings = get_settings()
    api_key = settings.serper_api_key.strip()
    if not api_key:
        raise ValueError("SERPER_API_KEY not configured")

    payload = {"q": query, "num": max(1, num_results)}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_SERPER_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return normalize_serper_results(data)


async def searxng_search(query: str, num_results: int = 10) -> list[dict[str, str]]:
    """Execute web search via SearXNG API."""
    settings = get_settings()
    base_url = settings.searxng_api_url.strip()
    if not base_url:
        raise ValueError("SEARXNG_API_URL not configured")

    url = _resolve_searxng_url(base_url)
    params = {
        "q": query,
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    results = normalize_searxng_results(data)
    if num_results > 0:
        results = results[: max(1, num_results)]
    return results


async def web_search(query: str, num_results: int = 10) -> tuple[str, list[dict[str, str]]]:
    """Search the web via Serper, falling back to SearXNG when configured."""
    settings = get_settings()
    last_error: Exception | None = None

    if settings.serper_api_key:
        try:
            results = await serper_search(query, num_results=num_results)
            return "serper", results
        except httpx.HTTPError as exc:
            last_error = exc

    if settings.searxng_api_url:
        try:
            results = await searxng_search(query, num_results=num_results)
            return "searxng", results
        except httpx.HTTPError as exc:
            last_error = exc

    if not settings.serper_api_key and not settings.searxng_api_url:
        raise ValueError("SERPER_API_KEY not configured")
    raise RuntimeError(f"Web search failed: {last_error}")
