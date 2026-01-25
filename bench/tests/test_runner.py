"""Tests for benchmark runner."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from janus_bench.config import Settings
from janus_bench.models import BenchmarkTask, Suite, TaskType
from janus_bench.runner import BenchmarkRunner


class TestBenchmarkRunner:
    """Tests for the BenchmarkRunner class."""

    @pytest.fixture
    def runner(self, settings):
        """Provide a runner instance."""
        return BenchmarkRunner(settings)

    @pytest.fixture
    def mock_sse_response(self):
        """Provide mock SSE response data."""
        chunks = [
            json.dumps({
                "id": "chatcmpl-123",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": "test-model",
                "choices": [{"index": 0, "delta": {"role": "assistant"}}],
            }),
            json.dumps({
                "id": "chatcmpl-123",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": "test-model",
                "choices": [{"index": 0, "delta": {"content": "The answer"}}],
            }),
            json.dumps({
                "id": "chatcmpl-123",
                "object": "chat.completion.chunk",
                "created": 1234567890,
                "model": "test-model",
                "choices": [{"index": 0, "delta": {"content": " is 4."}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }),
            "[DONE]",
        ]
        return [f"data: {chunk}\n\n" for chunk in chunks]

    def test_build_content_text_only(self, runner, sample_task):
        """Test building content for text-only task."""
        content = runner._build_content(sample_task)
        assert content == sample_task.prompt

    def test_build_content_multimodal(self, runner):
        """Test building content for multimodal task."""
        task = BenchmarkTask(
            id="multi_001",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.MULTIMODAL,
            prompt="Describe this image",
            image_url="data:image/png;base64,abc123",
        )
        content = runner._build_content(task)

        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "Describe this image"
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/png;base64,abc123"

    def test_has_image_input_from_messages(self, runner):
        """Test image detection from message overrides."""
        task = BenchmarkTask(
            id="multi_002",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.MULTIMODAL,
            prompt="Describe this image",
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is shown?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
                ],
            }
        ]

        assert runner._has_image_input(task, messages) is True

    @pytest.mark.asyncio
    async def test_run_task_success(self, runner, sample_task, mock_sse_response):
        """Test running a task successfully."""
        # Mock the HTTP client
        mock_response = AsyncMock()
        mock_response.status_code = 200

        async def mock_aiter_lines():
            for line in mock_sse_response:
                yield line.strip()

        mock_response.aiter_lines = mock_aiter_lines

        # Create async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(runner.client, "stream", return_value=mock_context):
            result = await runner.run_task(sample_task)

        assert result.task_id == sample_task.id
        assert result.success is True
        assert "4" in result.response_text
        assert result.streaming_metrics is not None
        assert result.streaming_metrics.total_chunks == 3
        assert result.total_tokens == 15

        # Clean up
        await runner.close()

    @pytest.mark.asyncio
    async def test_run_task_research_scoring_override(self, runner, mock_sse_response):
        """Test research scoring override uses judge output."""
        research_task = BenchmarkTask(
            id="research_001",
            suite=Suite.JANUS_INTELLIGENCE,
            type=TaskType.RESEARCH,
            prompt="Verify a claim with citations.",
            benchmark="janus_research",
            metadata={"research_task_type": "fact_verification"},
        )

        mock_response = AsyncMock()
        mock_response.status_code = 200

        async def mock_aiter_lines():
            for line in mock_sse_response:
                yield line.strip()

        mock_response.aiter_lines = mock_aiter_lines

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(runner.client, "stream", return_value=mock_context):
            with patch.object(
                runner,
                "_score_research_task",
                return_value=(0.9, {"quality_override": True}, 0.9, {"score": 0.9}),
            ):
                result = await runner.run_task(research_task)

        assert result.quality_score == 0.9
        assert result.metadata["quality_override"] is True
        assert result.judge_score == 0.9
        assert result.judge_output == {"score": 0.9}

        await runner.close()

    @pytest.mark.asyncio
    async def test_run_task_http_error(self, runner, sample_task):
        """Test handling HTTP error."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.aread = AsyncMock(return_value=b"Internal Server Error")

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(runner.client, "stream", return_value=mock_context):
            result = await runner.run_task(sample_task)

        assert result.success is False
        assert result.error is not None
        assert "500" in result.error

        await runner.close()

    @pytest.mark.asyncio
    async def test_run_task_tool_calls_mark_success(self, runner):
        """Tool-call-only responses should still be successful."""
        tool_task = BenchmarkTask(
            id="tool_001",
            suite=Suite.PUBLIC_DEV,
            type=TaskType.TOOL_USE,
            prompt="Call get_weather for Paris",
            metadata={"tool_use_task_type": "function_calling"},
        )

        tool_chunks = [
            json.dumps(
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": "{\"location\":\"Paris\"}",
                                        },
                                    }
                                ]
                            },
                        }
                    ],
                }
            ),
            "[DONE]",
        ]

        async def mock_aiter_lines():
            for chunk in tool_chunks:
                yield f"data: {chunk}"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(runner.client, "stream", return_value=mock_context):
            result = await runner.run_task(tool_task)

        assert result.success is True
        assert result.metadata
        assert result.metadata["first_token_received"] is True
        assert result.metadata["tool_calls"][0]["function"] == "get_weather"

        await runner.close()

    @pytest.mark.asyncio
    async def test_run_task_ttft_timeout(self, sample_task):
        """TTFT timeouts should surface as task errors."""
        settings = Settings(
            target_url="http://localhost:8000",
            model="test-model",
            request_timeout=30,
            ttft_timeout=0.001,
        )
        runner = BenchmarkRunner(settings)

        async def slow_aiter_lines():
            await asyncio.sleep(0.01)
            yield "data: [DONE]"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = slow_aiter_lines

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        with patch.object(runner.client, "stream", return_value=mock_context):
            result = await runner.run_task(sample_task)

        assert result.success is False
        assert result.error
        assert "TTFT timeout" in result.error

        await runner.close()

    def test_runner_initialization(self, settings):
        """Test runner initialization with custom settings."""
        runner = BenchmarkRunner(settings)

        assert runner.settings.target_url == settings.target_url
        assert runner.settings.model == settings.model
        assert runner.client is not None

    def test_runner_default_settings(self):
        """Test runner initialization with default settings."""
        runner = BenchmarkRunner()

        assert runner.settings is not None
        assert runner.settings.target_url == "http://localhost:8000"
