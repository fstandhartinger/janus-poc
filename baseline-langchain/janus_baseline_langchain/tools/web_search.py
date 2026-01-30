"""Web search tool for the LangChain baseline."""

import json
import time
from typing import Any, cast

import httpx
from langchain_core.tools import tool
from tavily import TavilyClient

from janus_baseline_langchain.config import get_settings

_SERPER_URL = "https://google.serper.dev/search"


def _search_with_retries(query: str, max_results: int) -> dict[str, object]:
    settings = get_settings()
    client = TavilyClient(api_key=settings.tavily_api_key)
    last_exc: Exception | None = None
    attempts = max(1, settings.max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            result = client.search(
                query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
            )
            return cast(dict[str, object], result)
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(0.5 * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("Search failed")


def _resolve_search_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/api/search"):
        return base
    if base.endswith("/api"):
        return f"{base}/search"
    if base.endswith("/search"):
        return base
    return f"{base}/api/search"


def _resolve_searxng_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/search"):
        return base
    return f"{base}/search"


def _search_serper(query: str, max_results: int) -> dict[str, object]:
    settings = get_settings()
    if not settings.serper_api_key:
        raise ValueError("SERPER_API_KEY not configured")
    response = httpx.post(
        _SERPER_URL,
        json={"q": query, "num": max_results},
        headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    return cast(dict[str, object], response.json())


def _search_searxng(query: str, max_results: int) -> dict[str, object]:
    settings = get_settings()
    if not settings.searxng_api_url:
        raise ValueError("SEARXNG_API_URL not configured")
    url = _resolve_searxng_url(settings.searxng_api_url)
    response = httpx.get(
        url,
        params={"q": query, "format": "json"},
        timeout=20,
    )
    response.raise_for_status()
    payload = cast(dict[str, object], response.json())
    if isinstance(payload.get("results"), list):
        payload["results"] = payload["results"][: max(1, max_results)]
    return payload


def _search_chutes(query: str, max_results: int) -> dict[str, object]:
    settings = get_settings()
    url = _resolve_search_url(settings.chutes_search_url)
    headers = {"Content-Type": "application/json"}
    if settings.chutes_api_key:
        headers["Authorization"] = f"Bearer {settings.chutes_api_key}"
    response = httpx.post(
        url,
        json={"query": query, "max_results": max_results},
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    return cast(dict[str, object], response.json())


def _normalize_results(raw: Any) -> list[dict[str, object]]:
    if isinstance(raw, dict) and isinstance(raw.get("results"), list):
        return cast(list[dict[str, object]], raw.get("results"))
    if isinstance(raw, dict) and isinstance(raw.get("organic"), list):
        organic = cast(list[dict[str, object]], raw.get("organic"))
        normalized: list[dict[str, object]] = []
        for item in organic:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("link") or item.get("url") or "",
                    "snippet": item.get("snippet") or item.get("description") or "",
                }
            )
        return normalized
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        data = raw.get("data") or {}
        if isinstance(data.get("results"), list):
            return cast(list[dict[str, object]], data.get("results"))
    if isinstance(raw, list):
        return cast(list[dict[str, object]], raw)
    return []


def _filter_valid_results(results: list[dict[str, object]]) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        url = str(result.get("url") or result.get("link") or "")
        snippet = str(result.get("snippet") or result.get("content") or "")
        if url and snippet and len(snippet) > 50:
            filtered.append(result)
    return filtered


@tool("web_search")
def web_search(query: str) -> str:
    """Search the web for up-to-date information."""
    settings = get_settings()
    last_error: Exception | None = None

    if settings.tavily_api_key:
        try:
            result = _search_with_retries(query, max_results=5)
            normalized = _normalize_results(result)
            filtered = _filter_valid_results(normalized)
            if filtered:
                result["results"] = filtered
            return json.dumps(result)
        except Exception as exc:
            last_error = exc

    if settings.serper_api_key:
        try:
            result = _search_serper(query, max_results=5)
            normalized = _normalize_results(result)
            filtered = _filter_valid_results(normalized)
            payload = {
                "query": query,
                "source": "serper",
                "results": filtered or normalized,
            }
            return json.dumps(payload)
        except Exception as exc:
            last_error = exc

    if settings.searxng_api_url:
        try:
            result = _search_searxng(query, max_results=5)
            normalized = _normalize_results(result)
            filtered = _filter_valid_results(normalized)
            payload = {
                "query": query,
                "source": "searxng",
                "results": filtered or normalized,
            }
            return json.dumps(payload)
        except Exception as exc:
            last_error = exc

    try:
        result = _search_chutes(query, max_results=5)
        normalized = _normalize_results(result)
        filtered = _filter_valid_results(normalized)
        payload = {
            "query": query,
            "source": "chutes-search",
            "results": filtered or normalized,
        }
        return json.dumps(payload)
    except Exception as exc:
        last_error = last_error or exc

    return f"Web search failed: {last_error}"


web_search_tool = web_search
