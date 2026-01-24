"""Smoke tests for multimodal tasks."""

import pytest

from tests.utils import assert_contains_any, assert_response_quality, is_mock_response, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestMultimodalTasks:
    """Test image, audio, and video capabilities."""

    async def test_image_generation_simple(self, client):
        """Agent generates an image from text description."""
        response = await send_message(client, "Generate an image of a sunset over mountains.")
        assert_contains_any(response, ["http", "data:image", "image", "generated"])

    async def test_image_generation_detailed(self, client):
        """Agent handles detailed image prompts."""
        response = await send_message(
            client,
            "Create a photorealistic image of a cozy coffee shop interior with warm lighting.",
        )
        assert_contains_any(response, ["image", "http", "photo"])

    async def test_text_to_speech(self, client):
        """Agent generates speech audio from text."""
        response = await send_message(
            client,
            "Convert this text to speech: 'Hello, welcome to Janus!'",
        )
        assert_contains_any(response, ["audio", "speech", "http", "wav"])

    async def test_image_analysis(self, client):
        """Agent analyzes/describes an image."""
        test_image = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+"
            "M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        response = await send_message(
            client,
            f"Describe this image: {test_image}",
            images=[test_image],
        )
        assert_response_quality(response)

    async def test_multimodal_workflow(self, client):
        """Agent handles complex multimodal workflows."""
        response = await send_message(
            client,
            "Generate an image of a robot, then describe what you generated.",
        )
        assert_contains_any(response, ["image", "robot"])
