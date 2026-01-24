"""Integration tests for tool execution."""

import os

import pytest

from janus_baseline_langchain.tools import (
    code_execution_tool,
    image_generation_tool,
    web_search_tool,
)


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.asyncio
async def test_web_search_returns_results() -> None:
    """Web search tool returns actual results."""
    if not os.getenv("BASELINE_LANGCHAIN_TAVILY_API_KEY"):
        pytest.skip("Missing BASELINE_LANGCHAIN_TAVILY_API_KEY")

    result = await web_search_tool.ainvoke("Python programming")
    assert result


@pytest.mark.asyncio
async def test_image_generation_returns_url() -> None:
    """Image generation returns a valid URL."""
    if not os.getenv("BASELINE_LANGCHAIN_CHUTES_API_KEY"):
        pytest.skip("Missing BASELINE_LANGCHAIN_CHUTES_API_KEY")

    result = await image_generation_tool.ainvoke("A red circle")
    assert "http" in result or "data:image" in result


@pytest.mark.asyncio
async def test_code_execution_runs_safely() -> None:
    """Code execution runs in sandbox."""
    result = await code_execution_tool.ainvoke("print(2 + 2)")
    assert "4" in result
