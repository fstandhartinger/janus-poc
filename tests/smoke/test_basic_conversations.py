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
        history: list[dict[str, object]] = []
        first = await send_message(client, "My name is Alice.", history=history)
        history.extend(
            [
                {"role": "user", "content": "My name is Alice."},
                {"role": "assistant", "content": first},
            ]
        )
        response = await send_message(client, "What's my name?", history=history)
        if not is_mock_response(response):
            assert "alice" in response.lower()

    async def test_follow_up_questions(self, client):
        """Agent handles follow-up questions with implicit references."""
        history: list[dict[str, object]] = []
        first = await send_message(client, "Tell me about Python programming.", history=history)
        history.extend(
            [
                {"role": "user", "content": "Tell me about Python programming."},
                {"role": "assistant", "content": first},
            ]
        )
        response = await send_message(client, "What are its main advantages?", history=history)
        assert_contains_any(response, ["python", "readability", "library"])

    async def test_correction_handling(self, client):
        """Agent accepts corrections gracefully."""
        history: list[dict[str, object]] = []
        first = await send_message(client, "The capital of Australia is Sydney.", history=history)
        history.extend(
            [
                {"role": "user", "content": "The capital of Australia is Sydney."},
                {"role": "assistant", "content": first},
            ]
        )
        response = await send_message(client, "Actually, it's Canberra.", history=history)
        assert_contains_any(response, ["canberra", "correct"])

    async def test_clarification_request(self, client):
        """Agent asks for clarification on ambiguous requests."""
        response = await send_message(client, "Make it better.")
        if not is_mock_response(response):
            assert "?" in response or "what" in response.lower() or "clarif" in response.lower()
