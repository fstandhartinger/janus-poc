"""Smoke tests for basic conversation flows."""

import pytest

from tests.utils import assert_contains_any, assert_response_quality, is_mock_response, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestBasicConversations:
    """Test fundamental chat capabilities."""

    async def test_simple_greeting(self, client):
        """Agent responds appropriately to greetings."""
        response = await send_message(client, "Hello! How are you?")
        assert_response_quality(response)

    async def test_factual_question(self, client):
        """Agent answers factual questions correctly."""
        response = await send_message(client, "What is the capital of France?")
        if not is_mock_response(response):
            assert "paris" in response.lower()

    async def test_multi_turn_context(self, client):
        """Agent maintains context across turns."""
        await send_message(client, "My name is Alice.")
        response = await send_message(client, "What's my name?")
        if not is_mock_response(response):
            assert "alice" in response.lower()

    async def test_follow_up_questions(self, client):
        """Agent handles follow-up questions with implicit references."""
        await send_message(client, "Tell me about Python programming.")
        response = await send_message(client, "What are its main advantages?")
        assert_contains_any(response, ["python", "readability", "library"])

    async def test_correction_handling(self, client):
        """Agent accepts corrections gracefully."""
        await send_message(client, "The capital of Australia is Sydney.")
        response = await send_message(client, "Actually, it's Canberra.")
        assert_contains_any(response, ["canberra", "correct"])

    async def test_clarification_request(self, client):
        """Agent asks for clarification on ambiguous requests."""
        response = await send_message(client, "Make it better.")
        if not is_mock_response(response):
            assert "?" in response or "what" in response.lower() or "clarif" in response.lower()
