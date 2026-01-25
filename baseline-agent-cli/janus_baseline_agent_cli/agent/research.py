"""Research prompt and response helpers."""

from __future__ import annotations

from typing import Any

RESEARCH_SYSTEM_PROMPT = """You are a research assistant. When answering questions:

1. **Always search first**: Use the web_search tool before answering any factual question.

2. **Cite your sources**: After every factual claim, include a citation like [1], [2], etc.

3. **Include a sources section**: At the end of your response, list all sources:

   **Sources:**
   [1] Title - URL
   [2] Title - URL

4. **Verify facts**: Cross-reference information from multiple sources when possible.

5. **Be specific**: Include dates, numbers, and specific details from your research.
"""


async def enhance_research_response(
    response: str,
    search_results: list[dict[str, Any]],
) -> str:
    """Post-process research responses to ensure proper citations."""
    if not response:
        return response

    if "**Sources:**" not in response and "Sources:" not in response:
        sources_section = "\n\n**Sources:**\n"
        for i, result in enumerate(search_results[:5], 1):
            title = result.get("title") or "Untitled"
            url = result.get("url") or ""
            sources_section += f"[{i}] {title} - {url}\n"
        response += sources_section

    return response
