"""Smoke tests for code generation and execution tasks."""

import pytest

from tests.utils import (
    assert_contains_any,
    assert_response_quality,
    assert_valid_python,
    extract_code_blocks,
    is_mock_response,
    send_message,
)

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class TestCodeTasks:
    """Test code generation and execution capabilities."""

    async def test_write_python_function(self, client):
        """Agent writes working Python code."""
        response = await send_message(client, "Write a Python function to calculate factorial.")
        assert_response_quality(response)
        if not is_mock_response(response):
            assert "def " in response
            assert "factorial" in response.lower()
            assert_valid_python(extract_code_blocks(response))

    async def test_execute_calculation(self, client):
        """Agent executes code and returns results."""
        response = await send_message(client, "Calculate 2^10 using Python code.")
        assert_contains_any(response, ["1024"])

    async def test_debug_code(self, client):
        """Agent identifies and fixes bugs in code."""
        buggy_code = """
        def add_numbers(a, b):
            return a - b  # Bug: should be +
        """
        response = await send_message(
            client,
            f"Fix the bug in this code:\n```python\n{buggy_code}\n```",
        )
        assert_contains_any(response, ["+", "addition"])

    async def test_explain_code(self, client):
        """Agent explains code clearly."""
        code = """
        def quicksort(arr):
            if len(arr) <= 1:
                return arr
            pivot = arr[len(arr) // 2]
            left = [x for x in arr if x < pivot]
            middle = [x for x in arr if x == pivot]
            right = [x for x in arr if x > pivot]
            return quicksort(left) + middle + right
        """
        response = await send_message(client, f"Explain this code:\n```python\n{code}\n```")
        assert_contains_any(response, ["quicksort", "sort", "pivot"])

    async def test_refactor_code(self, client):
        """Agent refactors code for improvement."""
        messy_code = """
        def f(x):
            y = x * 2
            z = y + 1
            return z
        """
        response = await send_message(
            client,
            f"Refactor this code for readability:\n```python\n{messy_code}\n```",
        )
        assert_response_quality(response)

    async def test_multi_language_code(self, client):
        """Agent handles multiple programming languages."""
        response = await send_message(client, "Write a function to reverse a string in JavaScript.")
        assert_contains_any(response, ["function", "=>", "reverse"])

    async def test_code_with_dependencies(self, client):
        """Agent installs and uses dependencies."""
        response = await send_message(
            client,
            "Use the requests library to fetch https://httpbin.org/get and show the response.",
        )
        assert_contains_any(response, ["requests", "httpbin"])

    async def test_file_manipulation_code(self, client):
        """Agent writes code that manipulates files."""
        response = await send_message(
            client,
            "Write Python code to read a CSV file and calculate the average of a numeric column.",
        )
        assert_contains_any(response, ["csv", "pandas", "average", "mean"])
