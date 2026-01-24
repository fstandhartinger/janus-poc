"""Smoke tests for complex, multi-step tasks."""

import pytest

from tests.utils import assert_contains_any, assert_response_quality, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestComplexTasks:
    """Test complex, multi-step task completion."""

    async def test_research_and_summarize(self, client):
        """Agent researches a topic and creates a summary."""
        response = await send_message(
            client,
            "Research the history of Bitcoin, write a 200-word summary, and save it to a file called bitcoin_summary.md",
        )
        assert_contains_any(response, ["bitcoin", "summary"])

    async def test_data_analysis_pipeline(self, client):
        """Agent performs end-to-end data analysis."""
        response = await send_message(
            client,
            """
            1. Generate sample sales data for 12 months
            2. Calculate monthly averages
            3. Identify the best and worst months
            4. Create a summary report
            """,
        )
        assert_contains_any(response, ["best", "worst", "january", "february", "march"])

    async def test_api_integration(self, client):
        """Agent integrates with an external API."""
        response = await send_message(
            client,
            "Fetch the current weather for London using a public API and tell me the temperature.",
        )
        assert_contains_any(response, ["temperature", "weather", "celsius", "fahrenheit", "degrees"])

    async def test_multi_tool_orchestration(self, client):
        """Agent uses multiple tools in sequence."""
        response = await send_message(
            client,
            """
            1. Search the web for "Python best practices 2024"
            2. Summarize the top 5 recommendations
            3. Write example code demonstrating one of them
            """,
        )
        assert_contains_any(response, ["python", "def ", "```", "recommendation"])

    async def test_creative_content_generation(self, client):
        """Agent generates creative content."""
        response = await send_message(
            client,
            "Write a haiku about artificial intelligence, then generate an image to accompany it.",
        )
        assert_response_quality(response)

    async def test_problem_decomposition(self, client):
        """Agent breaks down complex problems."""
        response = await send_message(
            client,
            "I want to build a todo app. What are the main components I need and how should I structure the code?",
        )
        assert_contains_any(response, ["component", "frontend", "backend", "database", "api"])

    async def test_iterative_refinement(self, client):
        """Agent iteratively refines output based on feedback."""
        await send_message(client, "Write a function to sort a list.")
        response = await send_message(client, "Now make it work with custom comparison functions.")
        assert_contains_any(response, ["key", "compare", "lambda"])
