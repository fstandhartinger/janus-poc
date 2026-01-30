"""FastAPI server for composite model routing.

Supports both OpenAI Chat Completions and Anthropic Messages API formats.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, AsyncIterator, Literal, Optional

import httpx
import structlog
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from classifier import RoutingDecisionClassifier
from metrics import metrics
from models import ModelConfig, get_fallback_models, get_model_for_decision
from decisions import (
    RoutingDecision,
    decision_for_images,
    decision_from_metadata,
    decision_from_model_id,
    decision_requires_agent,
)

logger = structlog.get_logger()

app = FastAPI(title="Janus Composite Model Router", version="1.1.0")

classifier: Optional[RoutingDecisionClassifier] = None
api_key: str = ""
api_base: str = "https://llm.chutes.ai/v1"


class ChatCompletionRequest(BaseModel):
    """Minimal OpenAI-compatible chat request for routing."""

    model: str
    messages: list[dict]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Any] = None

    model_config = ConfigDict(extra="allow")


# --- Anthropic Messages API Models ---


class AnthropicContentBlock(BaseModel):
    """Anthropic content block."""

    type: Literal["text", "image", "tool_use", "tool_result"] = "text"
    text: Optional[str] = None
    source: Optional[dict] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[dict] = None
    tool_use_id: Optional[str] = None
    content: Optional[str | list[dict]] = None


class AnthropicMessage(BaseModel):
    """Anthropic message."""

    role: Literal["user", "assistant"]
    content: str | list[AnthropicContentBlock | dict]


class AnthropicMessagesRequest(BaseModel):
    """Anthropic Messages API request."""

    model: str
    messages: list[AnthropicMessage]
    max_tokens: int = Field(default=4096)
    system: Optional[str | list[dict]] = None
    stop_sequences: Optional[list[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    metadata: Optional[dict] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[dict] = None

    model_config = ConfigDict(extra="allow")


class AnthropicUsage(BaseModel):
    """Anthropic token usage."""

    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicResponse(BaseModel):
    """Anthropic Messages API response."""

    id: str
    type: str = "message"
    role: str = "assistant"
    content: list[dict]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage


# --- Anthropic Format Conversion Helpers ---


def _extract_system_text(system: Optional[str | list[dict]]) -> Optional[str]:
    """Extract system text from Anthropic system field."""
    if isinstance(system, str):
        return system
    if isinstance(system, list):
        parts = []
        for block in system:
            text = block.get("text") or block.get("content")
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts) if parts else None
    return None


def _extract_anthropic_content_text(
    content: str | list[AnthropicContentBlock | dict],
) -> str:
    """Extract text from Anthropic content blocks."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif "text" in block:
                parts.append(block.get("text", ""))
        elif isinstance(block, AnthropicContentBlock):
            if block.type == "text" and block.text:
                parts.append(block.text)
    return " ".join(parts).strip()


def _anthropic_tools_to_openai(tools: Optional[list[dict]]) -> Optional[list[dict]]:
    """Convert Anthropic tool definitions to OpenAI tool format."""
    if not tools:
        return None
    openai_tools: list[dict] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name")
        if not name:
            continue
        function = {"name": name}
        description = tool.get("description")
        if description:
            function["description"] = description
        parameters = tool.get("input_schema") or tool.get("parameters")
        if parameters:
            function["parameters"] = parameters
        openai_tools.append({"type": "function", "function": function})
    return openai_tools or None


def _anthropic_tool_choice_to_openai(tool_choice: Any) -> Any:
    """Convert Anthropic tool_choice to OpenAI tool_choice."""
    if tool_choice is None:
        return None
    if isinstance(tool_choice, str):
        choice = tool_choice.lower()
        if choice == "auto":
            return "auto"
        if choice == "any":
            return "required"
        if choice == "none":
            return "none"
        return None
    if isinstance(tool_choice, dict):
        choice_type = tool_choice.get("type")
        if choice_type == "tool":
            name = tool_choice.get("name")
            if name:
                return {"type": "function", "function": {"name": name}}
            return "required"
        if choice_type == "auto":
            return "auto"
        if choice_type == "any":
            return "required"
        if choice_type == "none":
            return "none"
    return None


def _coerce_tool_content(content: Any) -> str:
    """Normalize tool result content to string."""
    if content is None:
        return ""
    if isinstance(content, (dict, list)):
        return json.dumps(content)
    return str(content)


def _anthropic_to_openai_messages(
    anthropic_request: AnthropicMessagesRequest,
) -> list[dict]:
    """Convert Anthropic messages to OpenAI format."""
    openai_messages = []

    # Add system message if present
    system_text = _extract_system_text(anthropic_request.system)
    if system_text:
        openai_messages.append({"role": "system", "content": system_text})

    # Convert each message
    for msg in anthropic_request.messages:
        if isinstance(msg.content, str):
            openai_messages.append({"role": msg.role, "content": msg.content})
            continue

        text_parts: list[str] = []
        tool_calls: list[dict] = []
        tool_results: list[dict] = []

        for block in msg.content:
            block_dict: dict[str, Any]
            if isinstance(block, AnthropicContentBlock):
                block_dict = block.model_dump()
            elif isinstance(block, dict):
                block_dict = block
            else:
                continue

            block_type = block_dict.get("type")
            if block_type == "text":
                text = block_dict.get("text") or ""
                if text:
                    text_parts.append(text)
            elif block_type == "tool_use" and msg.role == "assistant":
                tool_id = block_dict.get("id") or f"tool_{uuid.uuid4().hex[:8]}"
                name = block_dict.get("name") or ""
                input_obj = block_dict.get("input") or {}
                tool_calls.append(
                    {
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(input_obj),
                        },
                    }
                )
            elif block_type == "tool_result" and msg.role == "user":
                tool_use_id = block_dict.get("tool_use_id") or block_dict.get("id")
                tool_results.append(
                    {
                        "tool_call_id": tool_use_id,
                        "content": _coerce_tool_content(block_dict.get("content")),
                    }
                )

        text_content = "\n".join(text_parts).strip()

        if msg.role == "assistant":
            if text_content or tool_calls:
                openai_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": text_content,
                }
                if tool_calls:
                    openai_message["tool_calls"] = tool_calls
                openai_messages.append(openai_message)
        else:
            if text_content:
                openai_messages.append({"role": msg.role, "content": text_content})
            for tool_result in tool_results:
                if tool_result.get("tool_call_id"):
                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_result["tool_call_id"],
                            "content": tool_result["content"],
                        }
                    )

    return openai_messages


def _openai_to_anthropic_response(
    openai_response: dict,
    requested_model: str,
) -> dict:
    """Convert OpenAI response to Anthropic format."""
    choice = (openai_response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []
    finish_reason = choice.get("finish_reason")

    # Map OpenAI finish reasons to Anthropic stop reasons
    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "content_filter": "end_turn",
    }
    stop_reason = "tool_use" if tool_calls else stop_reason_map.get(finish_reason, "end_turn")

    usage = openai_response.get("usage", {})

    content_blocks: list[dict] = []
    if text:
        content_blocks.append({"type": "text", "text": text})
    for tool_call in tool_calls:
        function = tool_call.get("function") or {}
        name = function.get("name") or tool_call.get("name") or ""
        args = function.get("arguments") or {}
        input_obj: dict[str, Any]
        if isinstance(args, str):
            if args.strip():
                try:
                    input_obj = json.loads(args)
                except Exception:
                    input_obj = {"_raw": args}
            else:
                input_obj = {}
        elif isinstance(args, dict):
            input_obj = args
        else:
            input_obj = {}
        content_blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id") or f"toolu_{uuid.uuid4().hex[:8]}",
                "name": name,
                "input": input_obj,
            }
        )
    if not content_blocks:
        content_blocks.append({"type": "text", "text": ""})

    return AnthropicResponse(
        id=f"msg_{uuid.uuid4().hex[:24]}",
        type="message",
        role="assistant",
        content=content_blocks,
        model=requested_model,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=AnthropicUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        ),
    ).model_dump()


@app.on_event("startup")
async def startup() -> None:
    global classifier, api_key, api_base
    api_key = os.environ.get("CHUTES_API_KEY", "")
    api_base = (
        os.environ.get("CHUTES_API_BASE")
        or os.environ.get("CHUTES_API_URL")
        or "https://llm.chutes.ai/v1"
    )
    classifier = RoutingDecisionClassifier(api_key, api_base)


@app.on_event("shutdown")
async def shutdown() -> None:
    if classifier:
        await classifier.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "janus-router"}


@app.get("/v1/models")
async def list_models() -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": "janus-router",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "janus",
            }
        ],
    }


@app.get("/v1/router/metrics")
async def get_metrics() -> dict:
    """Return routing metrics."""
    return metrics.to_dict()


async def _resolve_routing_decision(
    messages: list[dict],
    has_images: bool,
    metadata: Optional[dict],
    requested_model: str,
    path_hint: Literal["fast", "agent"] | None = None,
) -> tuple[RoutingDecision, float, str, float]:
    start_time = time.perf_counter()
    decision = decision_from_metadata(metadata)
    if decision:
        return decision, 1.0, "metadata", (time.perf_counter() - start_time) * 1000

    decision = decision_from_model_id(requested_model, path_hint)
    if decision:
        return decision, 0.9, "model_override", (time.perf_counter() - start_time) * 1000

    if classifier is None:
        return RoutingDecision.FAST_NEMOTRON, 0.5, "default", (
            time.perf_counter() - start_time
        ) * 1000

    decision, confidence = await classifier.classify(messages, has_images)
    return decision, confidence, "classifier", (time.perf_counter() - start_time) * 1000


# --- Anthropic Messages API Endpoint ---


@app.post("/v1/messages")
async def anthropic_messages(
    request: AnthropicMessagesRequest,
    raw_request: Request,
    http_response: Response,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    anthropic_version: Optional[str] = Header(None, alias="anthropic-version"),
    anthropic_beta: Optional[str] = Header(None, alias="anthropic-beta"),
) -> Any:
    """Anthropic Messages API compatible endpoint.

    Claude Code and other Anthropic SDK clients use this endpoint.
    Converts requests to OpenAI format, routes to Chutes, converts response back.
    """
    requested_model = request.model

    # Convert Anthropic messages to OpenAI format
    openai_messages = _anthropic_to_openai_messages(request)
    has_images = _detect_images(openai_messages)

    decision, confidence, decision_source, classification_time_ms = await _resolve_routing_decision(
        openai_messages,
        has_images,
        request.metadata if isinstance(request.metadata, dict) else None,
        requested_model,
        path_hint="agent",
    )
    if has_images:
        decision = decision_for_images(decision_requires_agent(decision))

    primary_model = get_model_for_decision(decision)
    fallbacks = (
        []
        if decision_source in {"metadata", "model_override"}
        else get_fallback_models(primary_model.model_id)
    )

    logger.info(
        "anthropic_router_decision",
        decision=decision.value,
        confidence=confidence,
        model=primary_model.model_id,
        requested_model=requested_model,
        decision_source=decision_source,
        classification_time_ms=round(classification_time_ms, 2),
    )

    http_response.headers["X-Janus-Routing-Decision"] = decision.value
    http_response.headers["X-Janus-Routing-Model"] = primary_model.model_id

    models_to_try = [primary_model] + fallbacks
    last_error: Exception | None = None

    for index, model_config in enumerate(models_to_try):
        used_fallback = index > 0
        try:
            if request.stream:
                response = await _anthropic_stream_response(
                    request, openai_messages, model_config, decision
                )
            else:
                response = await _anthropic_non_stream_response(
                    request, openai_messages, model_config, decision
                )

            metrics.record_request(
                decision=decision.value,
                model_id=model_config.model_id,
                classification_time_ms=classification_time_ms,
                used_fallback=used_fallback,
            )
            return response
        except httpx.HTTPStatusError as exc:
            last_error = exc
            metrics.record_error(model_config.model_id)
            status = exc.response.status_code
            if status == 429:
                logger.warning("anthropic_router_rate_limited", model=model_config.model_id)
                continue
            if status >= 500:
                logger.warning(
                    "anthropic_router_model_error", model=model_config.model_id, status=status
                )
                continue
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        except Exception as exc:
            last_error = exc
            metrics.record_error(model_config.model_id)
            logger.warning(
                "anthropic_router_model_exception", model=model_config.model_id, error=str(exc)
            )
            continue

    raise HTTPException(status_code=503, detail=f"All models failed. Last error: {last_error}")


async def _anthropic_stream_response(
    anthropic_request: AnthropicMessagesRequest,
    openai_messages: list[dict],
    model_config: ModelConfig,
    routing_decision: RoutingDecision,
) -> StreamingResponse:
    """Stream response in Anthropic SSE format."""
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    openai_tools = _anthropic_tools_to_openai(anthropic_request.tools)
    openai_tool_choice = _anthropic_tool_choice_to_openai(anthropic_request.tool_choice)

    async def stream_from_message(message: dict) -> AsyncIterator[str]:
        message_start = {
            "type": "message_start",
            "message": {
                "id": message.get("id", msg_id),
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": message.get("model", anthropic_request.model),
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": (message.get("usage") or {}).get("input_tokens", 0),
                    "output_tokens": 0,
                },
            },
        }
        yield f"event: message_start\ndata: {json.dumps(message_start)}\n\n"

        content_blocks = message.get("content") or []
        for index, block in enumerate(content_blocks):
            content_block_start = {
                "type": "content_block_start",
                "index": index,
                "content_block": block,
            }
            yield f"event: content_block_start\ndata: {json.dumps(content_block_start)}\n\n"
            if block.get("type") == "text":
                text = block.get("text") or ""
                if text:
                    content_delta = {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": text},
                    }
                    yield f"event: content_block_delta\ndata: {json.dumps(content_delta)}\n\n"
            elif block.get("type") == "tool_use":
                input_obj = block.get("input") or {}
                partial_json = json.dumps(input_obj)
                if partial_json:
                    content_delta = {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "input_json_delta", "partial_json": partial_json},
                    }
                    yield f"event: content_block_delta\ndata: {json.dumps(content_delta)}\n\n"
            content_block_stop = {"type": "content_block_stop", "index": index}
            yield f"event: content_block_stop\ndata: {json.dumps(content_block_stop)}\n\n"

        message_delta = {
            "type": "message_delta",
            "delta": {
                "stop_reason": message.get("stop_reason"),
                "stop_sequence": message.get("stop_sequence"),
            },
            "usage": {
                "output_tokens": (message.get("usage") or {}).get("output_tokens", 0)
            },
        }
        yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n"
        yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'

    async def stream_generator():
        max_tokens = anthropic_request.max_tokens or model_config.max_tokens
        if max_tokens > model_config.max_tokens:
            max_tokens = model_config.max_tokens
        payload = {
            "model": model_config.model_id,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if anthropic_request.temperature is not None:
            payload["temperature"] = anthropic_request.temperature
        if anthropic_request.stop_sequences:
            payload["stop"] = anthropic_request.stop_sequences
        if openai_tools:
            payload["tools"] = openai_tools
        if openai_tool_choice is not None:
            payload["tool_choice"] = openai_tool_choice
        metadata = dict(anthropic_request.metadata or {})
        metadata["routing_decision"] = routing_decision.value
        payload["metadata"] = metadata

        # If tools are present, use non-streaming OpenAI call and stream the Anthropic response.
        if openai_tools or openai_tool_choice is not None:
            async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={**payload, "stream": False},
                )
                response.raise_for_status()
                openai_data = response.json()
            anthropic_message = _openai_to_anthropic_response(openai_data, anthropic_request.model)
            async for chunk in stream_from_message(anthropic_message):
                yield chunk
            return

        # Stream from OpenAI endpoint and convert to Anthropic deltas
        async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={**payload, "stream": True},
            ) as response:
                response.raise_for_status()

                # Send message_start event
                message_start = {
                    "type": "message_start",
                    "message": {
                        "id": msg_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": anthropic_request.model,
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                }
                yield f"event: message_start\ndata: {json.dumps(message_start)}\n\n"

                # Send content_block_start
                content_block_start = {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
                yield f"event: content_block_start\ndata: {json.dumps(content_block_start)}\n\n"

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = (data.get("choices") or [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            # Send content_block_delta
                            content_delta = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": content},
                            }
                            yield f"event: content_block_delta\ndata: {json.dumps(content_delta)}\n\n"
                    except json.JSONDecodeError:
                        continue

                # Send content_block_stop
                content_block_stop = {"type": "content_block_stop", "index": 0}
                yield f"event: content_block_stop\ndata: {json.dumps(content_block_stop)}\n\n"

                # Send message_delta
                message_delta = {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": 0},
                }
                yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n"

                # Send message_stop
                yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Janus-Model": model_config.model_id,
            "X-Janus-Routing-Decision": routing_decision.value,
            "X-Janus-Routing-Model": model_config.model_id,
        },
    )


async def _anthropic_non_stream_response(
    anthropic_request: AnthropicMessagesRequest,
    openai_messages: list[dict],
    model_config: ModelConfig,
    routing_decision: RoutingDecision,
) -> dict:
    """Return non-streaming Anthropic format response."""
    max_tokens = anthropic_request.max_tokens or model_config.max_tokens
    if max_tokens > model_config.max_tokens:
        max_tokens = model_config.max_tokens
    payload = {
        "model": model_config.model_id,
        "messages": openai_messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if anthropic_request.temperature is not None:
        payload["temperature"] = anthropic_request.temperature
    if anthropic_request.stop_sequences:
        payload["stop"] = anthropic_request.stop_sequences
    openai_tools = _anthropic_tools_to_openai(anthropic_request.tools)
    openai_tool_choice = _anthropic_tool_choice_to_openai(anthropic_request.tool_choice)
    if openai_tools:
        payload["tools"] = openai_tools
    if openai_tool_choice is not None:
        payload["tool_choice"] = openai_tool_choice
    metadata = dict(anthropic_request.metadata or {})
    metadata["routing_decision"] = routing_decision.value
    payload["metadata"] = metadata

    async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        openai_data = response.json()
        return _openai_to_anthropic_response(openai_data, anthropic_request.model)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_request: Request,
    http_response: Response,
) -> Any:
    """Classify and route chat completion requests."""
    has_images = _detect_images(request.messages)
    requested_model = request.model

    decision, confidence, decision_source, classification_time_ms = await _resolve_routing_decision(
        request.messages,
        has_images,
        request.metadata if isinstance(request.metadata, dict) else None,
        requested_model,
        path_hint="fast",
    )
    if has_images:
        decision = decision_for_images(decision_requires_agent(decision))

    primary_model = get_model_for_decision(decision)
    fallbacks = (
        []
        if decision_source in {"metadata", "model_override"}
        else get_fallback_models(primary_model.model_id)
    )

    logger.info(
        "router_decision",
        decision=decision.value,
        confidence=confidence,
        model=primary_model.model_id,
        classification_time_ms=round(classification_time_ms, 2),
        decision_source=decision_source,
    )

    http_response.headers["X-Janus-Routing-Decision"] = decision.value
    http_response.headers["X-Janus-Routing-Model"] = primary_model.model_id

    models_to_try = [primary_model] + fallbacks
    last_error: Exception | None = None

    for index, model_config in enumerate(models_to_try):
        used_fallback = index > 0
        try:
            if request.stream:
                response = await _stream_response(request, model_config, decision)
            else:
                response = await _non_stream_response(request, model_config, decision)

            metrics.record_request(
                decision=decision.value,
                model_id=model_config.model_id,
                classification_time_ms=classification_time_ms,
                used_fallback=used_fallback,
            )
            return response
        except httpx.HTTPStatusError as exc:
            last_error = exc
            metrics.record_error(model_config.model_id)
            status = exc.response.status_code
            if status == 429:
                logger.warning("router_rate_limited", model=model_config.model_id)
                continue
            if status >= 500:
                logger.warning("router_model_error", model=model_config.model_id, status=status)
                continue
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        except Exception as exc:
            last_error = exc
            metrics.record_error(model_config.model_id)
            logger.warning("router_model_exception", model=model_config.model_id, error=str(exc))
            continue

    raise HTTPException(status_code=503, detail=f"All models failed. Last error: {last_error}")


async def _stream_response(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
    routing_decision: RoutingDecision,
) -> StreamingResponse:
    """Stream response from the backend model."""

    async def stream_generator():
        async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=_build_payload(request, model_config, stream=True, decision=routing_decision),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            continue
                        try:
                            data = json.loads(payload)
                            data["model"] = "janus-router"
                            yield f"data: {json.dumps(data)}\n\n"
                        except json.JSONDecodeError:
                            yield f"{line}\n\n"
                    else:
                        yield f"{line}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Janus-Model": model_config.model_id,
            "X-Janus-Routing-Decision": routing_decision.value,
            "X-Janus-Routing-Model": model_config.model_id,
        },
    )


async def _non_stream_response(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
    routing_decision: RoutingDecision,
) -> dict:
    """Return non-streaming response from backend model."""
    async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=_build_payload(request, model_config, stream=False, decision=routing_decision),
        )
        response.raise_for_status()
        data = response.json()
        data["model"] = "janus-router"
        return data


def _build_payload(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
    stream: bool,
    decision: RoutingDecision | None = None,
) -> dict:
    payload = request.model_dump(exclude_none=True)
    if decision is not None:
        metadata = dict(payload.get("metadata") or {})
        metadata["routing_decision"] = decision.value
        payload["metadata"] = metadata
    payload["model"] = model_config.model_id
    payload["stream"] = stream
    # Clamp max_tokens to model's configured limit (prevents slow tool-heavy calls)
    max_tokens = request.max_tokens or model_config.max_tokens
    if max_tokens > model_config.max_tokens:
        max_tokens = model_config.max_tokens
    payload["max_tokens"] = max_tokens
    return payload


def _detect_images(messages: list[dict]) -> bool:
    """Detect if message payload contains image content."""
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


def run_router(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the router server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_router()
