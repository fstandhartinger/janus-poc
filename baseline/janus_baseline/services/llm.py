"""LLM service for fast-path completions."""

import uuid
from functools import lru_cache
from typing import AsyncGenerator, Optional

import structlog
from openai import AsyncOpenAI

from janus_baseline.config import Settings, get_settings
from janus_baseline.models import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChunkChoice,
    Delta,
    FinishReason,
    Message,
    MessageRole,
    Usage,
)

logger = structlog.get_logger()


class LLMService:
    """Service for making LLM calls via OpenAI-compatible API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._settings.openai_api_key or "dummy-key",
                base_url=self._settings.openai_base_url,
            )
        return self._client

    def _generate_id(self) -> str:
        """Generate a completion ID."""
        return f"chatcmpl-baseline-{uuid.uuid4().hex[:12]}"

    async def complete(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Make a non-streaming completion request."""
        client = self._get_client()
        request_id = self._generate_id()

        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": m.role.value, "content": m.content}
                for m in request.messages
                if m.content is not None
            ]

            response = await client.chat.completions.create(
                model=request.model or self._settings.model,
                messages=openai_messages,  # type: ignore
                temperature=request.temperature or self._settings.temperature,
                max_tokens=request.max_tokens or self._settings.max_tokens,
                stream=False,
            )

            # Convert response
            return ChatCompletionResponse(
                id=request_id,
                model=response.model,
                choices=[
                    Choice(
                        index=c.index,
                        message=Message(
                            role=MessageRole(c.message.role),
                            content=c.message.content,
                        ),
                        finish_reason=FinishReason(c.finish_reason) if c.finish_reason else None,
                    )
                    for c in response.choices
                ],
                usage=Usage(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0,
                ) if response.usage else None,
            )
        except Exception as e:
            logger.error("llm_completion_error", error=str(e))
            # Return error response
            return ChatCompletionResponse(
                id=request_id,
                model=request.model or self._settings.model,
                choices=[
                    Choice(
                        message=Message(
                            role=MessageRole.ASSISTANT,
                            content=f"Error: {e}",
                        ),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )

    async def stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Make a streaming completion request."""
        client = self._get_client()
        request_id = self._generate_id()
        model = request.model or self._settings.model

        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": m.role.value, "content": m.content}
                for m in request.messages
                if m.content is not None
            ]

            # Emit initial role chunk
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
            )

            # Emit reasoning content (thinking)
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(reasoning_content="Processing request... "))],
            )

            stream = await client.chat.completions.create(
                model=model,
                messages=openai_messages,  # type: ignore
                temperature=request.temperature or self._settings.temperature,
                max_tokens=request.max_tokens or self._settings.max_tokens,
                stream=True,
            )

            prompt_tokens = 0
            completion_tokens = 0

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason

                    yield ChatCompletionChunk(
                        id=request_id,
                        model=model,
                        choices=[
                            ChunkChoice(
                                delta=Delta(content=delta.content if delta.content else None),
                                finish_reason=FinishReason(finish_reason) if finish_reason else None,
                            )
                        ],
                    )

                    if delta.content:
                        completion_tokens += 1  # Rough estimate

                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens

            # Emit final chunk with usage if requested
            if request.stream_options and request.stream_options.include_usage:
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[],
                    usage=Usage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                    ),
                )

        except Exception as e:
            logger.error("llm_stream_error", error=str(e))
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[
                    ChunkChoice(
                        delta=Delta(content=f"\n\nError: {e}"),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )


@lru_cache
def get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService(get_settings())
