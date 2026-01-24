"""Smoke tests for file operations."""

import pytest

from tests.utils import assert_contains_any, assert_response_quality, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestFileOperations:
    """Test file reading, writing, and manipulation."""

    async def test_read_file(self, client):
        """Agent reads file contents."""
        response = await send_message(
            client,
            "Read the file at /workspace/test_data/sample.txt and summarize it.",
        )
        assert_response_quality(response)

    async def test_write_file(self, client):
        """Agent creates a file with content."""
        response = await send_message(client, "Create a file called output.txt containing 'Hello World'.")
        assert_contains_any(response, ["created", "written", "file"])

    async def test_list_directory(self, client):
        """Agent lists directory contents."""
        response = await send_message(client, "List all files in /workspace")
        assert_response_quality(response)

    async def test_process_csv(self, client):
        """Agent processes a CSV file."""
        response = await send_message(
            client,
            """
            Create a CSV file with this data:
            name,age,city
            Alice,30,NYC
            Bob,25,LA

            Then calculate the average age.
            """,
        )
        assert_contains_any(response, ["27.5", "average"])

    async def test_json_manipulation(self, client):
        """Agent manipulates JSON data."""
        response = await send_message(
            client,
            """
            Create a JSON file with user data, then add a new field 'active: true' to each user.
            """,
        )
        assert_contains_any(response, ["json", "active"])
