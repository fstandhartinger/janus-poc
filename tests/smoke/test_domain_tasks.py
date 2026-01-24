"""Smoke tests for domain-specific tasks."""

import pytest

from tests.utils import assert_contains_any, send_message

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestDomainTasks:
    """Test domain-specific use cases."""

    async def test_math_problem_solving(self, client):
        """Agent solves math problems."""
        response = await send_message(
            client,
            "Solve: If a train travels 120 miles in 2 hours, what is its speed in mph?",
        )
        assert_contains_any(response, ["60"])

    async def test_translation(self, client):
        """Agent translates between languages."""
        response = await send_message(client, "Translate 'Hello, how are you?' to Spanish.")
        assert_contains_any(response, ["hola"])

    async def test_data_formatting(self, client):
        """Agent formats data as requested."""
        response = await send_message(
            client,
            "Convert this to a markdown table: Name: Alice, Age: 30; Name: Bob, Age: 25",
        )
        assert_contains_any(response, ["|", "-"])

    async def test_regex_generation(self, client):
        """Agent creates regex patterns."""
        response = await send_message(client, "Write a regex to match email addresses.")
        assert_contains_any(response, ["@", "regex"])

    async def test_sql_generation(self, client):
        """Agent writes SQL queries."""
        response = await send_message(
            client,
            "Write a SQL query to find users older than 30 from a 'users' table.",
        )
        assert_contains_any(response, ["select"])

    async def test_shell_command_assistance(self, client):
        """Agent helps with shell commands."""
        response = await send_message(
            client,
            "How do I find all .py files in a directory recursively using bash?",
        )
        assert_contains_any(response, ["find", "*.py"])

    async def test_git_workflow(self, client):
        """Agent assists with git operations."""
        response = await send_message(
            client,
            "How do I undo my last git commit but keep the changes?",
        )
        assert_contains_any(response, ["reset", "git"])

    async def test_docker_assistance(self, client):
        """Agent helps with Docker."""
        response = await send_message(client, "Write a Dockerfile for a Python Flask app.")
        assert_contains_any(response, ["from", "dockerfile"])
