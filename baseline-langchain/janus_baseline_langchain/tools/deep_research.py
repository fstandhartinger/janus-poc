"""Deep research tool for LangChain baseline."""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import asyncio

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.services import get_request_auth_token


class DeepResearchInput(BaseModel):
    """Input schema for deep research."""

    query: str = Field(description="Research query")
    mode: Literal["light", "max"] = Field(
        default="max", description="Research depth mode"
    )


def _format_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines = ["\n\nSources:\n"]
    for index, source in enumerate(sources, 1):
        title = source.get("title") or source.get("name") or source.get("url")
        url = source.get("url") or source.get("link")
        if title and url:
            lines.append(f"{index}. [{title}]({url})")
        elif url:
            lines.append(f"{index}. {url}")
        elif title:
            lines.append(f"{index}. {title}")
        else:
            lines.append(f"{index}. Source {index}")
    return "\n".join(lines)


def _extract_answer(payload: dict[str, Any]) -> str:
    for key in ("answer", "content", "response", "output", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if "choices" in payload and isinstance(payload["choices"], list):
        choice = payload["choices"][0] if payload["choices"] else {}
        if isinstance(choice, dict):
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content.strip()
    return json.dumps(payload)


class DeepResearchTool(BaseTool):
    name: str = "deep_research"
    description: str = (
        "Perform comprehensive research with citations via chutes-search. "
        "Use for complex questions that require multiple sources."
    )
    args_schema: type[BaseModel] = DeepResearchInput

    timeout_seconds: float = 120.0

    def _run(self, query: str, mode: str = "max") -> str:
        return asyncio.run(self._arun(query, mode))

    async def _arun(self, query: str, mode: str = "max") -> str:
        settings = get_settings()
        base_url = settings.chutes_search_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        token = get_request_auth_token() or settings.chutes_api_key
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "messages": [{"role": "user", "content": query}],
            "mode": mode,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{base_url}/api/chat",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            return f"Deep research failed: {exc}"

        if not isinstance(data, dict):
            return str(data)

        sources = []
        for key in ("sources", "citations", "references"):
            value = data.get(key)
            if isinstance(value, list):
                sources = value
                break

        answer = _extract_answer(data)
        formatted_sources = _format_sources(sources)
        return f"{answer}{formatted_sources}"


deep_research_tool = DeepResearchTool()
