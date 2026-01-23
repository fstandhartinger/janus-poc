"""Web search tool for the LangChain baseline."""

import json
import time
from typing import cast

from langchain_core.tools import tool
from tavily import TavilyClient

from janus_baseline_langchain.config import get_settings


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


@tool("web_search")
def web_search(query: str) -> str:
    """Search the web for up-to-date information."""
    settings = get_settings()
    if not settings.tavily_api_key:
        return "Web search unavailable: missing API key."

    try:
        result = _search_with_retries(query, max_results=5)
    except Exception as exc:
        return f"Web search failed: {exc}"

    return json.dumps(result)


web_search_tool = web_search
