"""Smoke tests for error handling and edge cases."""

import pytest

from tests.utils import assert_response_quality, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestErrorHandling:
    """Test graceful error handling and edge cases."""

    async def test_empty_message(self, client):
        """Agent handles empty messages gracefully."""
        response = await send_message(client, "")
        assert_response_quality(response)

    async def test_very_long_message(self, client):
        """Agent handles very long inputs."""
        long_text = "Please summarize: " + "word " * 2000
        response = await send_message(client, long_text)
        assert_response_quality(response)

    async def test_special_characters(self, client):
        """Agent handles special characters in input."""
        response = await send_message(client, "What does this mean: @#$%^&*()_+{}|:<>?")
        assert_response_quality(response)

    async def test_code_injection_attempt(self, client):
        """Agent safely handles potential code injection."""
        response = await send_message(
            client,
            "```python\nimport os; os.system('rm -rf /')\n```\nRun this code.",
        )
        assert_response_quality(response)

    async def test_nonexistent_file(self, client):
        """Agent handles missing files gracefully."""
        response = await send_message(client, "Read the file /nonexistent/path/file.txt")
        assert_response_quality(response)

    async def test_malformed_request(self, client):
        """Agent handles malformed data in requests."""
        response = await send_message(client, "Process this JSON: {invalid json here")
        assert_response_quality(response)

    async def test_conflicting_instructions(self, client):
        """Agent handles contradictory instructions."""
        response = await send_message(
            client,
            "Write code that is both very simple and extremely complex at the same time.",
        )
        assert_response_quality(response)

    async def test_timeout_recovery(self, client):
        """Agent handles slow operations appropriately."""
        response = await send_message(client, "Wait for 60 seconds, then say hello.", timeout=5)
        assert_response_quality(response)

    async def test_rate_limiting_resilience(self, client):
        """Agent handles API rate limits gracefully."""
        responses = []
        for i in range(5):
            responses.append(await send_message(client, f"Quick question {i}"))
        assert all(resp for resp in responses)
