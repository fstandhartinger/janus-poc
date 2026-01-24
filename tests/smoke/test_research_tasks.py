"""Smoke tests for research and web search tasks."""

import pytest

from tests.utils import assert_response_quality, is_mock_response, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestResearchTasks:
    """Test web search and research capabilities."""

    async def test_current_events_search(self, client):
        """Agent searches for recent information."""
        response = await send_message(client, "What are the latest developments in AI? Search the web.")
        assert_response_quality(response)
        if not is_mock_response(response):
            assert len(response) > 200

    async def test_specific_fact_lookup(self, client):
        """Agent looks up specific facts."""
        response = await send_message(client, "Search for the current population of Tokyo.")
        assert_response_quality(response)
        if not is_mock_response(response):
            assert any(char.isdigit() for char in response)

    async def test_comparison_research(self, client):
        """Agent researches and compares options."""
        response = await send_message(
            client,
            "Compare React and Vue.js for frontend development. Include pros and cons.",
        )
        if not is_mock_response(response):
            assert "react" in response.lower()
            assert "vue" in response.lower()

    async def test_source_citation(self, client):
        """Agent cites sources when researching."""
        response = await send_message(client, "What is the GDP of Germany? Cite your source.")
        if not is_mock_response(response):
            assert "http" in response or "source" in response.lower()

    async def test_synthesis_from_multiple_sources(self, client):
        """Agent synthesizes information from multiple sources."""
        response = await send_message(
            client,
            "Give me a comprehensive overview of quantum computing, including recent breakthroughs.",
        )
        assert_response_quality(response)
        if not is_mock_response(response):
            assert len(response) > 500
