"""LLM service for fast-path completions."""

import uuid
from functools import lru_cache
from typing import AsyncGenerator, Optional, cast

import structlog
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion as OpenAIChatCompletion,
    ChatCompletionChunk as OpenAIChatCompletionChunk,
)

from janus_baseline_agent_cli.config import Settings, get_settings
from janus_baseline_agent_cli.models import (
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
from janus_baseline_agent_cli.services.vision import contains_images

logger = structlog.get_logger()


class LLMService:
    """Service for making LLM calls via OpenAI-compatible API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Optional[AsyncOpenAI] = None
        self._vision_model_primary = settings.vision_model_primary
        self._vision_model_fallback = settings.vision_model_fallback
        self._vision_timeout = settings.vision_model_timeout
        self._enable_vision_routing = settings.enable_vision_routing

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

    def _should_mock(self) -> bool:
        return not self._settings.openai_api_key and not self._settings.openai_base_url

    def _mock_text(self) -> str:
        return (
            "Hello! The Janus Baseline is running in mock mode. "
            "Set BASELINE_AGENT_CLI_OPENAI_API_KEY to enable live responses."
        )

    def select_model(self, request: ChatCompletionRequest) -> str:
        """Select the appropriate model based on message content."""
        requested_model = request.model or self._settings.model
        if requested_model in {"baseline", "baseline-langchain"}:
            requested_model = self._settings.model
        if self._enable_vision_routing and contains_images(request.messages):
            logger.info(
                "vision_routing_enabled",
                model=self._vision_model_primary,
            )
            return self._vision_model_primary
        return requested_model

    def _is_vision_model(self, model: str) -> bool:
        return model in {self._vision_model_primary, self._vision_model_fallback}

    def _format_content(self, content) -> str | list:
        """Format content for API request."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content

        formatted: list[dict] = []
        for part in content:
            if isinstance(part, dict):
                formatted.append(part)
            elif hasattr(part, "model_dump"):
                formatted.append(part.model_dump())
            else:
                formatted.append({"type": "text", "text": str(part)})
        return formatted

    def _format_messages(self, request: ChatCompletionRequest) -> list[dict]:
        return [
            {"role": m.role.value, "content": self._format_content(m.content)}
            for m in request.messages
            if m.content is not None
        ]

    async def _create_completion(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: list[dict],
        request: ChatCompletionRequest,
        timeout: float,
        stream: bool,
    ):
        return await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=request.temperature or self._settings.temperature,
            max_tokens=request.max_tokens or self._settings.max_tokens,
            stream=stream,
            timeout=timeout,
        )

    async def complete(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Make a non-streaming completion request."""
        request_id = self._generate_id()

        if self._should_mock():
            logger.info("llm_mock_response", mode="non_streaming")
            return ChatCompletionResponse(
                id=request_id,
                model=self.select_model(request),
                choices=[
                    Choice(
                        message=Message(
                            role=MessageRole.ASSISTANT,
                            content=self._mock_text(),
                        ),
                        finish_reason=FinishReason.STOP,
                    )
                ],
                usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

        client = self._get_client()
        model = self.select_model(request)
        is_vision = self._is_vision_model(model)
        timeout = self._vision_timeout if is_vision else 30.0
        openai_messages = self._format_messages(request)

        try:
            response = cast(
                OpenAIChatCompletion,
                await self._create_completion(
                    client,
                    model=model,
                    messages=openai_messages,
                    request=request,
                    timeout=timeout,
                    stream=False,
                ),
            )
        except Exception as e:
            if is_vision and model == self._vision_model_primary:
                logger.warning(
                    "vision_primary_failed_fallback",
                    error=str(e),
                    fallback=self._vision_model_fallback,
                )
                try:
                    model = self._vision_model_fallback
                    response = cast(
                        OpenAIChatCompletion,
                        await self._create_completion(
                            client,
                            model=model,
                            messages=openai_messages,
                            request=request,
                            timeout=self._vision_timeout,
                            stream=False,
                        ),
                    )
                except Exception as fallback_exc:
                    logger.error(
                        "llm_completion_error",
                        error=str(fallback_exc),
                    )
                    return ChatCompletionResponse(
                        id=request_id,
                        model=model,
                        choices=[
                            Choice(
                                message=Message(
                                    role=MessageRole.ASSISTANT,
                                    content=f"Error: {fallback_exc}",
                                ),
                                finish_reason=FinishReason.STOP,
                            )
                        ],
                    )
            else:
                logger.error("llm_completion_error", error=str(e))
                return ChatCompletionResponse(
                    id=request_id,
                    model=model,
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

    async def stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Make a streaming completion request."""
        request_id = self._generate_id()
        model = self.select_model(request)
        is_vision = self._is_vision_model(model)
        timeout = self._vision_timeout if is_vision else 30.0

        if self._should_mock():
            logger.info("llm_mock_response", mode="streaming")
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(role=MessageRole.ASSISTANT))],
            )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(reasoning_content="Running in mock mode... "))],
            )
            for word in self._mock_text().split():
                yield ChatCompletionChunk(
                    id=request_id,
                    model=model,
                    choices=[ChunkChoice(delta=Delta(content=f"{word} "))],
                )
            yield ChatCompletionChunk(
                id=request_id,
                model=model,
                choices=[ChunkChoice(delta=Delta(), finish_reason=FinishReason.STOP)],
            )
            return

        client = self._get_client()
        openai_messages = self._format_messages(request)

        try:
            try:
                stream = cast(
                    AsyncStream[OpenAIChatCompletionChunk],
                    await self._create_completion(
                        client,
                        model=model,
                        messages=openai_messages,
                        request=request,
                        timeout=timeout,
                        stream=True,
                    ),
                )
            except Exception as exc:
                if is_vision and model == self._vision_model_primary:
                    logger.warning(
                        "vision_primary_stream_failed_fallback",
                        error=str(exc),
                        fallback=self._vision_model_fallback,
                    )
                    model = self._vision_model_fallback
                    stream = cast(
                        AsyncStream[OpenAIChatCompletionChunk],
                        await self._create_completion(
                            client,
                            model=model,
                            messages=openai_messages,
                            request=request,
                            timeout=self._vision_timeout,
                            stream=True,
                        ),
                    )
                else:
                    raise

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
