# Spec 58: Composite Model Router for Baseline Agent

## Status: DRAFT

## Context / Why

The baseline-agent-cli currently uses a single LLM model for all requests. This is suboptimal because:

1. **No specialization**: Different tasks benefit from different models:
   - Math problems → reasoning-optimized models
   - Image analysis → vision models
   - Programming → code-specialized models
   - Creative writing → story-focused models

2. **No fallback**: If the primary model returns HTTP 429 (rate limited) or 5xx errors, the entire request fails

3. **Inefficient routing**: Simple "what is 2+2?" queries use the same expensive model as complex multi-step reasoning

The solution is a **local OpenAI-compatible composite model router** that runs inside the sandbox, receives all LLM requests from the agent, classifies them using a fast/cheap model, and routes to the optimal backend model with automatic fallback.

## Goals

- Create a local OpenAI-compatible API server (runs on localhost:8000 inside sandbox)
- Use fast LLM-based classification to detect request type
- Route to specialized models based on classification
- Implement automatic fallback on errors (429, 5xx)
- Maintain full streaming compatibility
- Keep latency overhead minimal (< 200ms for classification)

## Non-Goals

- Creating new models
- Hosting models locally (all calls go to Chutes API)
- Caching responses (handled separately)
- Load balancing across providers (single provider: Chutes)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Sandy Sandbox                                  │
│                                                                          │
│  ┌──────────────────┐         ┌────────────────────────────────────┐    │
│  │   CLI Agent      │         │    Composite Model Router          │    │
│  │   (Aider, etc)   │         │    (localhost:8000)                │    │
│  │                  │         │                                    │    │
│  │  Configured to   │  HTTP   │  1. Receive request                │    │
│  │  use model:      │ ──────► │  2. Fast classify (GLM-4.7-Flash) │    │
│  │  "janus-router"  │         │  3. Route to optimal model         │    │
│  │                  │ ◄────── │  4. Stream response back           │    │
│  └──────────────────┘         │  5. Fallback on error              │    │
│                               └─────────────┬──────────────────────┘    │
│                                             │                            │
└─────────────────────────────────────────────│────────────────────────────┘
                                              │
                                              │ HTTPS (to Chutes API)
                                              ▼
                    ┌─────────────────────────────────────────────┐
                    │              Chutes API                      │
                    │                                              │
                    │  ┌───────────────────┐  ┌────────────────┐  │
                    │  │ GLM-4.7-Flash     │  │ DeepSeek V3.2  │  │
                    │  │ (classification)  │  │ (math/reason)  │  │
                    │  └───────────────────┘  └────────────────┘  │
                    │                                              │
                    │  ┌───────────────────┐  ┌────────────────┐  │
                    │  │ MiniMax-M2.1      │  │ Qwen3-VL       │  │
                    │  │ (programming)     │  │ (vision)       │  │
                    │  └───────────────────┘  └────────────────┘  │
                    │                                              │
                    │  ┌───────────────────┐  ┌────────────────┐  │
                    │  │ TNG-R1T2          │  │ GLM-4.7        │  │
                    │  │ (creative)        │  │ (general)      │  │
                    │  └───────────────────┘  └────────────────┘  │
                    └─────────────────────────────────────────────┘
```

## Functional Requirements

### FR-1: Model Registry

```python
# baseline-agent-cli/janus_baseline_agent_cli/router/models.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaskType(Enum):
    """Task types for routing decisions."""
    SIMPLE_TEXT = "simple_text"           # Quick factual answers
    GENERAL_TEXT = "general_text"         # Standard conversations
    MATH_REASONING = "math_reasoning"     # Math, logic, complex reasoning
    PROGRAMMING = "programming"           # Code generation, debugging
    CREATIVE = "creative"                 # Stories, roleplay, creative writing
    VISION = "vision"                     # Image understanding
    UNKNOWN = "unknown"                   # Fallback to general


@dataclass
class ModelConfig:
    """Configuration for a backend model."""
    model_id: str
    display_name: str
    task_types: list[TaskType]
    priority: int  # Lower = higher priority for fallback
    max_tokens: int = 8192
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    timeout_seconds: float = 120.0


# Model Registry - ordered by specialty
MODEL_REGISTRY: dict[str, ModelConfig] = {
    # Fast classification model (used internally)
    "classifier": ModelConfig(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash (Classifier)",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=0,
        max_tokens=1024,
        timeout_seconds=10.0,
    ),

    # Simple/fast queries
    "fast": ModelConfig(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=1,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),

    # General purpose
    "general": ModelConfig(
        model_id="zai-org/GLM-4.7-TEE",
        display_name="GLM 4.7",
        task_types=[TaskType.GENERAL_TEXT, TaskType.UNKNOWN],
        priority=2,
        max_tokens=8192,
        timeout_seconds=60.0,
    ),

    # Math and reasoning
    "reasoning": ModelConfig(
        model_id="deepseek-ai/DeepSeek-V3.2-Speciale-TEE",
        display_name="DeepSeek V3.2 Speciale",
        task_types=[TaskType.MATH_REASONING],
        priority=3,
        max_tokens=16384,
        timeout_seconds=120.0,
    ),

    # Programming
    "programming": ModelConfig(
        model_id="MiniMaxAI/MiniMax-M2.1-TEE",
        display_name="MiniMax M2.1",
        task_types=[TaskType.PROGRAMMING],
        priority=4,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),

    # Creative writing and roleplay
    "creative": ModelConfig(
        model_id="deepseek-ai/DeepSeek-TNG-R1T2-Chimera",
        display_name="TNG R1T2 Chimera",
        task_types=[TaskType.CREATIVE],
        priority=5,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),

    # Vision/multimodal
    "vision": ModelConfig(
        model_id="Qwen/Qwen3-VL-235B-A22B-Instruct",
        display_name="Qwen3 VL 235B",
        task_types=[TaskType.VISION],
        priority=6,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=90.0,
    ),

    # Vision fallback
    "vision_fallback": ModelConfig(
        model_id="zai-org/GLM-4.6V",
        display_name="GLM 4.6V",
        task_types=[TaskType.VISION],
        priority=7,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=60.0,
    ),

    # Alternative fast model
    "fast_alt": ModelConfig(
        model_id="XiaomiMiMo/MiMo-V2-Flash",
        display_name="MiMo V2 Flash",
        task_types=[TaskType.SIMPLE_TEXT, TaskType.GENERAL_TEXT],
        priority=8,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),
}


def get_model_for_task(task_type: TaskType) -> ModelConfig:
    """Get the primary model for a task type."""
    for config in sorted(MODEL_REGISTRY.values(), key=lambda c: c.priority):
        if task_type in config.task_types:
            return config
    return MODEL_REGISTRY["general"]


def get_fallback_models(primary_model_id: str) -> list[ModelConfig]:
    """Get fallback models when primary fails."""
    primary = next((c for c in MODEL_REGISTRY.values() if c.model_id == primary_model_id), None)
    if not primary:
        return [MODEL_REGISTRY["general"]]

    # Get models that handle similar tasks, ordered by priority
    fallbacks = []
    for config in sorted(MODEL_REGISTRY.values(), key=lambda c: c.priority):
        if config.model_id != primary_model_id:
            # Vision models only fallback to other vision models
            if primary.supports_vision and config.supports_vision:
                fallbacks.append(config)
            elif not primary.supports_vision and not config.supports_vision:
                fallbacks.append(config)

    return fallbacks[:3]  # Max 3 fallbacks
```

### FR-2: LLM-Based Task Classification

```python
# baseline-agent-cli/janus_baseline_agent_cli/router/classifier.py

import json
import httpx
from typing import Optional
from .models import TaskType, MODEL_REGISTRY

CLASSIFICATION_PROMPT = """You are a request classifier. Analyze the user's request and determine the best task type.

Available task types:
- simple_text: Quick factual questions, greetings, basic Q&A (e.g., "What is 2+2?", "Hello", "What's the capital of France?")
- general_text: Standard conversations, explanations, summaries (e.g., "Explain quantum computing", "Summarize this article")
- math_reasoning: Complex math, logic puzzles, proofs, multi-step reasoning (e.g., "Prove that √2 is irrational", "Solve this differential equation")
- programming: Code generation, debugging, code review, technical implementations (e.g., "Write a Python function to...", "Fix this bug", "Implement a REST API")
- creative: Stories, poems, roleplay, creative writing, fictional scenarios (e.g., "Write a story about...", "Continue this narrative", "Act as a character")
- vision: Requests that reference images or ask about visual content (e.g., "What's in this image?", "Describe this diagram")

Analyze the request and call the classify_task function with your decision.

IMPORTANT:
- If the request mentions "image", "picture", "photo", "screenshot", "diagram", or "visual" → vision
- If the request asks to write code, fix bugs, or implement features → programming
- If the request involves equations, proofs, or complex calculations → math_reasoning
- If the request asks for stories, roleplay, or creative content → creative
- If the request is a simple question with a short factual answer → simple_text
- Default to general_text for standard conversations"""

CLASSIFICATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_task",
            "description": "Classify the task type for optimal model routing",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["simple_text", "general_text", "math_reasoning", "programming", "creative", "vision"],
                        "description": "The classified task type"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score (0-1)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of classification"
                    }
                },
                "required": ["task_type", "confidence"]
            }
        }
    }
]


class TaskClassifier:
    """Classifies incoming requests to determine optimal routing."""

    def __init__(self, api_key: str, api_base: str = "https://llm.chutes.ai/v1"):
        self.api_key = api_key
        self.api_base = api_base
        self.model = MODEL_REGISTRY["classifier"]
        self.client = httpx.AsyncClient(timeout=self.model.timeout_seconds)

    async def classify(
        self,
        messages: list[dict],
        has_images: bool = False,
    ) -> tuple[TaskType, float]:
        """
        Classify a request to determine task type.

        Returns:
            Tuple of (TaskType, confidence_score)
        """
        # Fast path: if request has images, it's vision
        if has_images:
            return TaskType.VISION, 1.0

        # Fast path: very short messages are likely simple
        user_content = self._extract_user_content(messages)
        if len(user_content) < 50 and not any(kw in user_content.lower() for kw in [
            "write", "create", "implement", "code", "function", "class",
            "prove", "solve", "calculate", "equation", "story", "roleplay"
        ]):
            return TaskType.SIMPLE_TEXT, 0.8

        # Use LLM classification for complex cases
        try:
            response = await self.client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model.model_id,
                    "messages": [
                        {"role": "system", "content": CLASSIFICATION_PROMPT},
                        {"role": "user", "content": f"Classify this request:\n\n{user_content[:2000]}"},
                    ],
                    "tools": CLASSIFICATION_TOOLS,
                    "tool_choice": {"type": "function", "function": {"name": "classify_task"}},
                    "max_tokens": 100,
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Parse tool call response
            tool_calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
            if tool_calls:
                args = json.loads(tool_calls[0]["function"]["arguments"])
                task_type = TaskType(args["task_type"])
                confidence = args.get("confidence", 0.7)
                return task_type, confidence

        except Exception as e:
            # Log error but don't fail - fallback to general
            print(f"Classification error: {e}")

        return TaskType.GENERAL_TEXT, 0.5

    def _extract_user_content(self, messages: list[dict]) -> str:
        """Extract text content from user messages."""
        parts = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
        return " ".join(parts)

    async def close(self):
        await self.client.aclose()
```

### FR-3: Router Server

```python
# baseline-agent-cli/janus_baseline_agent_cli/router/server.py

import asyncio
import json
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
import httpx

from .models import (
    TaskType,
    ModelConfig,
    MODEL_REGISTRY,
    get_model_for_task,
    get_fallback_models,
)
from .classifier import TaskClassifier
from ..services.vision import contains_images

app = FastAPI(title="Janus Composite Model Router", version="1.0.0")

# Global state
classifier: Optional[TaskClassifier] = None
api_key: str = ""
api_base: str = "https://llm.chutes.ai/v1"


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Any] = None


@app.on_event("startup")
async def startup():
    global classifier, api_key, api_base
    import os
    api_key = os.environ.get("CHUTES_API_KEY", "")
    api_base = os.environ.get("CHUTES_API_BASE", "https://llm.chutes.ai/v1")
    classifier = TaskClassifier(api_key, api_base)


@app.on_event("shutdown")
async def shutdown():
    if classifier:
        await classifier.close()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "janus-router"}


@app.get("/v1/models")
async def list_models():
    """Return available models (the router itself)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "janus-router",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "janus",
            }
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, raw_request: Request):
    """
    Main routing endpoint. Classifies request and routes to optimal model.
    """
    start_time = time.time()

    # Detect if request contains images
    has_images = _detect_images(request.messages)

    # Classify the request
    task_type, confidence = await classifier.classify(request.messages, has_images)

    # Get primary model for this task type
    primary_model = get_model_for_task(task_type)
    fallbacks = get_fallback_models(primary_model.model_id)

    # Log routing decision
    classification_time = time.time() - start_time
    print(f"[Router] Task: {task_type.value} (confidence: {confidence:.2f})")
    print(f"[Router] Model: {primary_model.display_name}")
    print(f"[Router] Classification took: {classification_time*1000:.0f}ms")

    # Try primary model, then fallbacks
    models_to_try = [primary_model] + fallbacks
    last_error = None

    for model_config in models_to_try:
        try:
            if request.stream:
                return await _stream_response(request, model_config)
            else:
                return await _non_stream_response(request, model_config)

        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 429:
                print(f"[Router] Rate limited on {model_config.display_name}, trying fallback...")
                continue
            elif e.response.status_code >= 500:
                print(f"[Router] Server error on {model_config.display_name}, trying fallback...")
                continue
            else:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))

        except Exception as e:
            last_error = e
            print(f"[Router] Error on {model_config.display_name}: {e}")
            continue

    # All models failed
    raise HTTPException(
        status_code=503,
        detail=f"All models failed. Last error: {last_error}"
    )


async def _stream_response(
    request: ChatCompletionRequest,
    model_config: ModelConfig,
) -> StreamingResponse:
    """Stream response from backend model."""

    async def stream_generator():
        async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_config.model_id,
                    "messages": request.messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens or model_config.max_tokens,
                    "stream": True,
                    "tools": request.tools,
                    "tool_choice": request.tool_choice,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        # Rewrite model name in response
                        if line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
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
    """Get non-streaming response from backend model."""
    async with httpx.AsyncClient(timeout=model_config.timeout_seconds) as client:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_config.model_id,
                "messages": request.messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or model_config.max_tokens,
                "stream": False,
                "tools": request.tools,
                "tool_choice": request.tool_choice,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Rewrite model name
        data["model"] = "janus-router"
        return data


def _detect_images(messages: list[dict]) -> bool:
    """Detect if messages contain image content."""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


# Entry point
def run_router(host: str = "127.0.0.1", port: int = 8000):
    """Run the router server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_router()
```

### FR-4: Agent Configuration Update

```python
# baseline-agent-cli/janus_baseline_agent_cli/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Model Router Configuration
    use_model_router: bool = True
    router_host: str = "127.0.0.1"
    router_port: int = 8000

    # When using router, this is what agents see
    # The router translates to actual models
    model: str = "janus-router"

    # Direct model access (when router disabled)
    direct_model: str = "zai-org/GLM-4.7-TEE"

    # API Configuration
    chutes_api_key: str = ""
    chutes_api_base: str = "https://llm.chutes.ai/v1"

    @property
    def effective_api_base(self) -> str:
        """Get the API base URL (local router or Chutes direct)."""
        if self.use_model_router:
            return f"http://{self.router_host}:{self.router_port}/v1"
        return self.chutes_api_base

    @property
    def effective_model(self) -> str:
        """Get the effective model name."""
        if self.use_model_router:
            return "janus-router"
        return self.direct_model

    class Config:
        env_prefix = "BASELINE_"
```

### FR-5: Bootstrap Script Update

```bash
#!/bin/bash
# baseline-agent-cli/agent-pack/bootstrap.sh

# ... existing setup ...

# Start the model router in the background
echo "Starting Janus Model Router..."
python -m janus_baseline_agent_cli.router.server &
ROUTER_PID=$!

# Wait for router to be ready
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "Router ready!"
        break
    fi
    sleep 0.5
done

# Configure agent to use local router
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="${CHUTES_API_KEY}"
export OPENAI_MODEL="janus-router"

# ... rest of agent setup ...

# Cleanup on exit
trap "kill $ROUTER_PID 2>/dev/null" EXIT
```

### FR-6: Metrics and Logging

```python
# baseline-agent-cli/janus_baseline_agent_cli/router/metrics.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

@dataclass
class RoutingMetrics:
    """Metrics for routing decisions."""
    total_requests: int = 0
    requests_by_task_type: dict[str, int] = field(default_factory=dict)
    requests_by_model: dict[str, int] = field(default_factory=dict)
    fallback_count: int = 0
    errors_by_model: dict[str, int] = field(default_factory=dict)
    avg_classification_time_ms: float = 0.0
    classification_times: list[float] = field(default_factory=list)

    def record_request(
        self,
        task_type: str,
        model_id: str,
        classification_time_ms: float,
        used_fallback: bool = False,
    ):
        self.total_requests += 1
        self.requests_by_task_type[task_type] = self.requests_by_task_type.get(task_type, 0) + 1
        self.requests_by_model[model_id] = self.requests_by_model.get(model_id, 0) + 1
        if used_fallback:
            self.fallback_count += 1
        self.classification_times.append(classification_time_ms)
        self.avg_classification_time_ms = sum(self.classification_times) / len(self.classification_times)

    def record_error(self, model_id: str):
        self.errors_by_model[model_id] = self.errors_by_model.get(model_id, 0) + 1

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "requests_by_task_type": self.requests_by_task_type,
            "requests_by_model": self.requests_by_model,
            "fallback_count": self.fallback_count,
            "fallback_rate": self.fallback_count / max(self.total_requests, 1),
            "errors_by_model": self.errors_by_model,
            "avg_classification_time_ms": round(self.avg_classification_time_ms, 2),
        }


# Global metrics instance
metrics = RoutingMetrics()


# Add metrics endpoint to router
@app.get("/v1/router/metrics")
async def get_metrics():
    """Get routing metrics."""
    return metrics.to_dict()
```

### FR-7: Dockerfile Update

```dockerfile
# baseline-agent-cli/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && poetry export -f requirements.txt -o requirements.txt --without-hashes

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY janus_baseline_agent_cli/ ./janus_baseline_agent_cli/
COPY agent-pack/ ./agent-pack/

# Environment
ENV HOST=0.0.0.0
ENV PORT=8080
ENV BASELINE_USE_MODEL_ROUTER=true
ENV BASELINE_ROUTER_PORT=8000

# Health check targets the main API, not the router
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

# Start both router and main server
CMD ["sh", "-c", "python -m janus_baseline_agent_cli.router.server & sleep 2 && python -m janus_baseline_agent_cli.main"]
```

## Routing Decision Matrix

| Task Type | Primary Model | Fallback 1 | Fallback 2 |
|-----------|---------------|------------|------------|
| Simple Text | GLM-4.7-Flash | MiMo-V2-Flash | GLM-4.7 |
| General Text | GLM-4.7 | MiMo-V2-Flash | DeepSeek V3.2 |
| Math/Reasoning | DeepSeek V3.2 Speciale | GLM-4.7 | MiniMax M2.1 |
| Programming | MiniMax M2.1 | DeepSeek V3.2 | GLM-4.7 |
| Creative | TNG R1T2 | GLM-4.7 | DeepSeek V3.2 |
| Vision | Qwen3-VL-235B | GLM-4.6V | - |

## Error Handling

### HTTP 429 (Rate Limited)
1. Log the rate limit
2. Immediately try next fallback model
3. Track rate limit frequency per model
4. If all models rate limited, return 503

### HTTP 5xx (Server Error)
1. Log the error with model details
2. Try next fallback model
3. Track error frequency per model
4. If persistent, consider removing model from rotation

### Classification Failures
1. Fallback to GENERAL_TEXT task type
2. Use GLM-4.7 as default model
3. Log classification error for debugging

## Non-Functional Requirements

### NFR-1: Latency
- Classification overhead: < 200ms average
- Total added latency: < 250ms
- Fallback switch time: < 50ms

### NFR-2: Reliability
- 99.9% availability with fallbacks
- Graceful degradation on partial failures
- No single point of failure (except Chutes API)

### NFR-3: Observability
- Log all routing decisions
- Track metrics per model
- Expose metrics endpoint

## Acceptance Criteria

- [ ] Router server starts and exposes /v1/chat/completions
- [ ] Classification correctly identifies task types
- [ ] Vision requests route to vision models
- [ ] Programming requests route to MiniMax
- [ ] Math requests route to DeepSeek V3.2
- [ ] Creative requests route to TNG R1T2
- [ ] Fallback works on 429 errors
- [ ] Fallback works on 5xx errors
- [ ] Streaming works through router
- [ ] Metrics endpoint returns data
- [ ] Agent-cli works with router as API base
- [ ] Dockerfile starts both router and main server

## Files to Create

```
baseline-agent-cli/
├── janus_baseline_agent_cli/
│   └── router/
│       ├── __init__.py
│       ├── models.py         # Model registry
│       ├── classifier.py     # LLM-based classification
│       ├── server.py         # FastAPI router server
│       └── metrics.py        # Routing metrics
├── tests/
│   └── test_router.py        # Router tests
└── Dockerfile                # MODIFY
```

## Related Specs

- `specs/38_multimodal_vision_models.md` - Vision model support
- `specs/25_llm_complexity_second_pass.md` - LLM-based classification pattern
- `specs/54_baseline_containerization.md` - Container setup
- `specs/57_baseline_performance_optimization.md` - Performance improvements

## References

- [Chutes API Documentation](https://chutes.ai/docs)
- [OpenRouter Provider - Chutes](https://openrouter.ai/provider/chutes)
- chutes-webcoder model configuration
