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
    AssistantMessage,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChunkChoice,
    Delta,
    FinishReason,
    Message,
    MessageRole,
    ToolCall,
    Usage,
)
from janus_baseline_agent_cli.agent.efficiency import (
    optimize_system_prompt,
    truncate_context_intelligently,
)
from janus_baseline_agent_cli.services.vision import contains_images

logger = structlog.get_logger()


def _split_stream_content(content: str, max_chars: int = 40) -> list[str]:
    if len(content) <= max_chars:
        return [content]
    return [content[i : i + max_chars] for i in range(0, len(content), max_chars)]


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
            api_key = self._settings.effective_api_key or "dummy-key"
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._settings.effective_api_base,
            )
        return self._client

    def _generate_id(self) -> str:
        """Generate a completion ID."""
        return f"chatcmpl-baseline-{uuid.uuid4().hex[:12]}"

    def _should_mock(self) -> bool:
        return self._settings.effective_api_key is None

    def _mock_text(self) -> str:
        return (
            "Hello! The Janus Baseline is running in mock mode. "
            "Set BASELINE_AGENT_CLI_OPENAI_API_KEY to enable live responses."
        )

    def select_model(self, request: ChatCompletionRequest) -> str:
        """Select the appropriate model based on message content."""
        if self._settings.use_model_router:
            return self._settings.effective_model
        requested_model = request.model or self._settings.model
        if requested_model in {
            "baseline",
            "baseline-cli-agent",
            "baseline-langchain",
            "janus-baseline-agent-cli",
            "janus-baseline-langchain",
        }:
            requested_model = self._settings.model
        if requested_model == "janus-router":
            requested_model = self._settings.direct_model
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
        messages = truncate_context_intelligently(request.messages)
        task_type = self._infer_task_type(messages)
        formatted: list[dict] = []
        for message in messages:
            if message.content is None:
                continue
            content = self._format_content(message.content)
            if message.role == MessageRole.SYSTEM and isinstance(content, str):
                content = optimize_system_prompt(content, task_type)
            formatted.append({"role": message.role.value, "content": content})
        return formatted

    def _format_tools(self, request: ChatCompletionRequest) -> tuple[list[dict], object] | tuple[None, None]:
        if not request.tools:
            return None, None
        tools = []
        for tool in request.tools:
            if hasattr(tool, "model_dump"):
                tools.append(tool.model_dump())
            else:
                tools.append(tool)
        tool_choice = request.tool_choice
        if tool_choice is not None and hasattr(tool_choice, "model_dump"):
            tool_choice = tool_choice.model_dump()
        return tools, tool_choice

    def _convert_tool_calls(self, tool_calls: list[object]) -> list[ToolCall]:
        converted: list[ToolCall] = []
        for call in tool_calls:
            if hasattr(call, "model_dump"):
                payload = call.model_dump()
            elif isinstance(call, dict):
                payload = call
            else:
                function = getattr(call, "function", None)
                payload = {
                    "id": getattr(call, "id", "tool"),
                    "type": getattr(call, "type", "function"),
                    "function": {
                        "name": getattr(function, "name", ""),
                        "arguments": getattr(function, "arguments", ""),
                    },
                }
            try:
                converted.append(ToolCall(**payload))
            except Exception:
                continue
        return converted

    def _infer_task_type(self, messages: list[Message]) -> str:
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        if not user_messages:
            return "general"
        text = user_messages[-1].content
        if not isinstance(text, str):
            return "general"
        lowered = text.lower()
        if any(token in lowered for token in ("calculate", "equation", "solve", "math")):
            return "math"
        if any(token in lowered for token in ("code", "python", "script", "bug", "function")):
            return "code"
        if any(token in lowered for token in ("story", "poem", "creative", "write a")):
            return "creative"
        if any(token in lowered for token in ("what is", "who is", "when is", "where is")):
            return "factual"
        return "simple_qa"

    async def _create_completion(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: list[dict],
        request: ChatCompletionRequest,
        timeout: float,
        stream: bool,
    ):
        tools, tool_choice = self._format_tools(request)
        tool_params: dict[str, object] = {}
        if tools:
            tool_params["tools"] = tools
            if tool_choice is not None:
                tool_params["tool_choice"] = tool_choice
        return await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=request.temperature or self._settings.temperature,
            max_tokens=request.max_tokens or self._settings.max_tokens,
            stream=stream,
            timeout=timeout,
            **tool_params,
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
                                    content="I'm sorry, I encountered an error processing your request. Please try again.",
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
                                content="I'm sorry, I encountered an error processing your request. Please try again.",
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
                    message=(
                        AssistantMessage(
                            content=c.message.content,
                            reasoning_content=getattr(c.message, "reasoning_content", None),
                            tool_calls=self._convert_tool_calls(c.message.tool_calls)
                            if c.message.tool_calls
                            else None,
                        )
                        if getattr(c.message, "tool_calls", None)
                        else Message(
                            role=MessageRole(c.message.role),
                            content=c.message.content,
                        )
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
                    tool_calls = (
                        self._convert_tool_calls(delta.tool_calls)
                        if getattr(delta, "tool_calls", None)
                        else None
                    )

                    content = delta.content or ""
                    content_parts = _split_stream_content(content) if content else []

                    if content_parts:
                        for index, part in enumerate(content_parts):
                            is_last = index == len(content_parts) - 1
                            yield ChatCompletionChunk(
                                id=request_id,
                                model=model,
                                choices=[
                                    ChunkChoice(
                                        delta=Delta(
                                            content=part,
                                            tool_calls=tool_calls if index == 0 else None,
                                        ),
                                        finish_reason=(
                                            FinishReason(finish_reason)
                                            if finish_reason and is_last
                                            else None
                                        ),
                                    )
                                ],
                            )
                            completion_tokens += 1  # Rough estimate
                    else:
                        yield ChatCompletionChunk(
                            id=request_id,
                            model=model,
                            choices=[
                                ChunkChoice(
                                    delta=Delta(content=None, tool_calls=tool_calls),
                                    finish_reason=FinishReason(finish_reason)
                                    if finish_reason
                                    else None,
                                )
                            ],
                        )

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
                        delta=Delta(content="\n\nI'm sorry, I encountered an error. Please try again."),
                        finish_reason=FinishReason.STOP,
                    )
                ],
            )


@lru_cache
def get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService(get_settings())
