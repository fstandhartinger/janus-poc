"""FastAPI server for composite model routing."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from .classifier import TaskClassifier
from .metrics import metrics
from .models import ModelConfig, TaskType, get_fallback_models, get_model_for_task

logger = structlog.get_logger()

app = FastAPI(title="Janus Composite Model Router", version="1.0.0")

classifier: Optional[TaskClassifier] = None
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


@app.on_event("startup")
async def startup() -> None:
    global classifier, api_key, api_base
    api_key = os.environ.get("CHUTES_API_KEY", "")
    api_base = (
        os.environ.get("CHUTES_API_BASE")
        or os.environ.get("CHUTES_API_URL")
        or "https://llm.chutes.ai/v1"
    )
    classifier = TaskClassifier(api_key, api_base)


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


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, raw_request: Request) -> Any:
    """Classify and route chat completion requests."""
    start_time = time.perf_counter()
    has_images = _detect_images(request.messages)

    if classifier is None:
        task_type, confidence = TaskType.GENERAL_TEXT, 0.5
    else:
        task_type, confidence = await classifier.classify(request.messages, has_images)

    classification_time_ms = (time.perf_counter() - start_time) * 1000

    primary_model = get_model_for_task(task_type)
    fallbacks = get_fallback_models(primary_model.model_id)

    logger.info(
        "router_decision",
        task_type=task_type.value,
        confidence=confidence,
        model=primary_model.model_id,
        classification_time_ms=round(classification_time_ms, 2),
    )

    models_to_try = [primary_model] + fallbacks
    last_error: Exception | None = None

    for index, model_config in enumerate(models_to_try):
        used_fallback = index > 0
        try:
            if request.stream:
                response = await _stream_response(request, model_config)
            else:
                response = await _non_stream_response(request, model_config)

            metrics.record_request(
                task_type=task_type.value,
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
                json=_build_payload(request, model_config, stream=True),
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
        },
    )


async def _non_stream_response(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
) -> dict:
    """Return non-streaming response from backend model."""
    async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=_build_payload(request, model_config, stream=False),
        )
        response.raise_for_status()
        data = response.json()
        data["model"] = "janus-router"
        return data


def _build_payload(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
    stream: bool,
) -> dict:
    payload = request.model_dump(exclude_none=True)
    payload["model"] = model_config.model_id
    payload["stream"] = stream
    payload["max_tokens"] = request.max_tokens or model_config.max_tokens
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
