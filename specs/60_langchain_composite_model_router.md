# Spec 59: LangChain Composite Model Router

## Status: COMPLETE

## Context / Why

The baseline-langchain implementation uses a single LLM model for all requests via LangChain's `ChatOpenAI`. Like the CLI baseline (Spec 58), this is suboptimal because different tasks benefit from specialized models.

However, LangChain provides a more elegant solution than running a separate router server. We can create a **custom ChatModel** that:
1. Wraps multiple backend models
2. Classifies requests before routing
3. Handles fallbacks natively within LangChain's abstractions
4. Integrates seamlessly with LangChain's agent, tools, and streaming

This approach is cleaner for LangChain because:
- No separate server process needed
- Native integration with LangChain callbacks and streaming
- Easier to extend with LangChain's RunnableRouter and conditional logic
- Better error handling through LangChain's retry mechanisms

## Goals

- Create a `CompositeRoutingChatModel` that implements LangChain's `BaseChatModel`
- Use fast LLM-based classification (reuse logic from Spec 58)
- Route to optimal models based on task type
- Implement automatic fallback on errors
- Maintain full streaming and callback compatibility
- Integrate with existing LangChain agent setup

## Non-Goals

- Running a separate router server (use Spec 58 approach instead)
- Changing the tool implementations
- Modifying the agent structure beyond model replacement

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         baseline-langchain                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        AgentExecutor                                 │    │
│  │                                                                      │    │
│  │  ┌────────────────────────────────────────────────────────────┐     │    │
│  │  │              CompositeRoutingChatModel                      │     │    │
│  │  │                                                             │     │    │
│  │  │  ┌──────────────┐    ┌─────────────────────────────────┐   │     │    │
│  │  │  │  Classifier  │    │       Model Registry            │   │     │    │
│  │  │  │  (GLM Flash) │    │                                 │   │     │    │
│  │  │  └──────┬───────┘    │  ┌─────────┐ ┌─────────────┐   │   │     │    │
│  │  │         │            │  │ GLM 4.7 │ │ DeepSeek    │   │   │     │    │
│  │  │         ▼            │  │ (fast)  │ │ V3.2        │   │   │     │    │
│  │  │  ┌──────────────┐    │  └─────────┘ └─────────────┘   │   │     │    │
│  │  │  │ Task Type    │    │                                 │   │     │    │
│  │  │  │ Detection    │───►│  ┌─────────┐ ┌─────────────┐   │   │     │    │
│  │  │  └──────────────┘    │  │ MiniMax │ │ Qwen VL     │   │   │     │    │
│  │  │                      │  │ M2.1    │ │ (vision)    │   │   │     │    │
│  │  │                      │  └─────────┘ └─────────────┘   │   │     │    │
│  │  │                      │                                 │   │     │    │
│  │  │                      │  ┌─────────┐                    │   │     │    │
│  │  │                      │  │ TNG R1T2│                    │   │     │    │
│  │  │                      │  │(creative)                    │   │     │    │
│  │  │                      │  └─────────┘                    │   │     │    │
│  │  │                      └─────────────────────────────────┘   │     │    │
│  │  └────────────────────────────────────────────────────────────┘     │    │
│  │                                                                      │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │    │
│  │  │ web_search │ │ image_gen  │ │    tts     │ │ code_exec  │        │    │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
                            ┌─────────────────┐
                            │   Chutes API    │
                            └─────────────────┘
```

## Functional Requirements

### FR-1: Model Registry (Shared with Spec 58)

```python
# baseline-langchain/janus_baseline_langchain/router/models.py

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class TaskType(Enum):
    """Task types for routing decisions."""
    SIMPLE_TEXT = "simple_text"
    GENERAL_TEXT = "general_text"
    MATH_REASONING = "math_reasoning"
    PROGRAMMING = "programming"
    CREATIVE = "creative"
    VISION = "vision"
    UNKNOWN = "unknown"


@dataclass
class ModelSpec:
    """Specification for a backend model."""
    model_id: str
    display_name: str
    task_types: list[TaskType]
    priority: int
    max_tokens: int = 8192
    supports_vision: bool = False
    timeout_seconds: float = 120.0
    temperature: float = 0.7


# Same registry as Spec 58
MODEL_SPECS: dict[str, ModelSpec] = {
    "classifier": ModelSpec(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash (Classifier)",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=0,
        max_tokens=1024,
        timeout_seconds=10.0,
        temperature=0.0,
    ),
    "fast": ModelSpec(
        model_id="zai-org/GLM-4.7-Flash",
        display_name="GLM 4.7 Flash",
        task_types=[TaskType.SIMPLE_TEXT],
        priority=1,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),
    "general": ModelSpec(
        model_id="zai-org/GLM-4.7-TEE",
        display_name="GLM 4.7",
        task_types=[TaskType.GENERAL_TEXT, TaskType.UNKNOWN],
        priority=2,
        max_tokens=8192,
        timeout_seconds=60.0,
    ),
    "reasoning": ModelSpec(
        model_id="deepseek-ai/DeepSeek-V3.2-Speciale-TEE",
        display_name="DeepSeek V3.2 Speciale",
        task_types=[TaskType.MATH_REASONING],
        priority=3,
        max_tokens=16384,
        timeout_seconds=120.0,
    ),
    "programming": ModelSpec(
        model_id="MiniMaxAI/MiniMax-M2.1-TEE",
        display_name="MiniMax M2.1",
        task_types=[TaskType.PROGRAMMING],
        priority=4,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),
    "creative": ModelSpec(
        model_id="deepseek-ai/DeepSeek-TNG-R1T2-Chimera",
        display_name="TNG R1T2 Chimera",
        task_types=[TaskType.CREATIVE],
        priority=5,
        max_tokens=16384,
        timeout_seconds=90.0,
    ),
    "vision": ModelSpec(
        model_id="Qwen/Qwen3-VL-235B-A22B-Instruct",
        display_name="Qwen3 VL 235B",
        task_types=[TaskType.VISION],
        priority=6,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=90.0,
    ),
    "vision_fallback": ModelSpec(
        model_id="zai-org/GLM-4.6V",
        display_name="GLM 4.6V",
        task_types=[TaskType.VISION],
        priority=7,
        max_tokens=8192,
        supports_vision=True,
        timeout_seconds=60.0,
    ),
    "fast_alt": ModelSpec(
        model_id="XiaomiMiMo/MiMo-V2-Flash",
        display_name="MiMo V2 Flash",
        task_types=[TaskType.SIMPLE_TEXT, TaskType.GENERAL_TEXT],
        priority=8,
        max_tokens=4096,
        timeout_seconds=30.0,
    ),
}


def get_model_for_task(task_type: TaskType) -> ModelSpec:
    """Get the primary model for a task type."""
    for spec in sorted(MODEL_SPECS.values(), key=lambda s: s.priority):
        if task_type in spec.task_types:
            return spec
    return MODEL_SPECS["general"]


def get_fallback_models(primary_model_id: str, is_vision: bool = False) -> list[ModelSpec]:
    """Get fallback models when primary fails."""
    fallbacks = []
    for spec in sorted(MODEL_SPECS.values(), key=lambda s: s.priority):
        if spec.model_id != primary_model_id:
            if is_vision and spec.supports_vision:
                fallbacks.append(spec)
            elif not is_vision and not spec.supports_vision:
                fallbacks.append(spec)
    return fallbacks[:3]
```

### FR-2: Task Classifier

```python
# baseline-langchain/janus_baseline_langchain/router/classifier.py

import json
from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from .models import TaskType, MODEL_SPECS

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
                        "enum": [t.value for t in TaskType if t != TaskType.UNKNOWN],
                        "description": "The classified task type"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score"
                    }
                },
                "required": ["task_type", "confidence"]
            }
        }
    }
]

CLASSIFICATION_SYSTEM = """Classify the user's request into one of these task types:
- simple_text: Quick factual questions, greetings, basic Q&A
- general_text: Standard conversations, explanations, summaries
- math_reasoning: Complex math, logic puzzles, proofs, multi-step reasoning
- programming: Code generation, debugging, code review
- creative: Stories, poems, roleplay, creative writing
- vision: Requests about images or visual content

Call classify_task with your decision."""


class TaskClassifier:
    """Classifies incoming requests using a fast LLM."""

    def __init__(self, api_key: str, base_url: str = "https://llm.chutes.ai/v1"):
        self.classifier_llm = ChatOpenAI(
            model=MODEL_SPECS["classifier"].model_id,
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=0,
            max_tokens=100,
            timeout=MODEL_SPECS["classifier"].timeout_seconds,
        )

    def classify(
        self,
        messages: Sequence[BaseMessage],
        has_images: bool = False,
    ) -> tuple[TaskType, float]:
        """
        Classify messages to determine task type.

        Returns:
            Tuple of (TaskType, confidence_score)
        """
        # Fast path: images -> vision
        if has_images:
            return TaskType.VISION, 1.0

        # Fast path: short simple messages
        user_content = self._extract_user_content(messages)
        if len(user_content) < 50 and not self._has_complex_keywords(user_content):
            return TaskType.SIMPLE_TEXT, 0.8

        # Use LLM classification
        try:
            response = self.classifier_llm.invoke(
                [
                    {"role": "system", "content": CLASSIFICATION_SYSTEM},
                    {"role": "user", "content": f"Classify: {user_content[:2000]}"},
                ],
                tools=CLASSIFICATION_TOOLS,
                tool_choice={"type": "function", "function": {"name": "classify_task"}},
            )

            if response.tool_calls:
                args = response.tool_calls[0]["args"]
                task_type = TaskType(args["task_type"])
                confidence = args.get("confidence", 0.7)
                return task_type, confidence

        except Exception as e:
            print(f"[Classifier] Error: {e}")

        return TaskType.GENERAL_TEXT, 0.5

    def _extract_user_content(self, messages: Sequence[BaseMessage]) -> str:
        """Extract text from user messages."""
        parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
        return " ".join(parts)

    def _has_complex_keywords(self, text: str) -> bool:
        """Check for keywords indicating complex tasks."""
        keywords = [
            "write", "create", "implement", "code", "function", "class",
            "prove", "solve", "calculate", "equation", "story", "roleplay",
            "explain", "analyze", "compare", "design", "build",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
```

### FR-3: Composite Routing Chat Model

```python
# baseline-langchain/janus_baseline_langchain/router/chat_model.py

import logging
from typing import Any, Iterator, List, Optional, Sequence, Union

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import Field, PrivateAttr
from pydantic.v1 import SecretStr

from .models import TaskType, ModelSpec, MODEL_SPECS, get_model_for_task, get_fallback_models
from .classifier import TaskClassifier

logger = logging.getLogger(__name__)


class CompositeRoutingChatModel(BaseChatModel):
    """
    A LangChain ChatModel that routes requests to optimal backend models.

    Features:
    - Classifies each request using a fast LLM
    - Routes to specialized models based on task type
    - Automatic fallback on errors (429, 5xx)
    - Full streaming support
    - Metrics tracking
    """

    api_key: str = Field(description="API key for Chutes")
    base_url: str = Field(default="https://llm.chutes.ai/v1", description="API base URL")
    default_temperature: float = Field(default=0.7, description="Default temperature")

    # Private attributes
    _classifier: Optional[TaskClassifier] = PrivateAttr(default=None)
    _model_cache: dict[str, ChatOpenAI] = PrivateAttr(default_factory=dict)
    _metrics: dict[str, int] = PrivateAttr(default_factory=lambda: {
        "total_requests": 0,
        "fallback_count": 0,
        "by_task_type": {},
        "by_model": {},
        "errors": {},
    })

    def __init__(self, **data):
        super().__init__(**data)
        self._classifier = TaskClassifier(self.api_key, self.base_url)
        self._model_cache = {}
        self._metrics = {
            "total_requests": 0,
            "fallback_count": 0,
            "by_task_type": {},
            "by_model": {},
            "errors": {},
        }

    @property
    def _llm_type(self) -> str:
        return "composite-routing"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"base_url": self.base_url}

    def _get_model(self, spec: ModelSpec) -> ChatOpenAI:
        """Get or create a ChatOpenAI instance for a model spec."""
        if spec.model_id not in self._model_cache:
            self._model_cache[spec.model_id] = ChatOpenAI(
                model=spec.model_id,
                api_key=SecretStr(self.api_key),
                base_url=self.base_url,
                temperature=spec.temperature,
                max_tokens=spec.max_tokens,
                timeout=spec.timeout_seconds,
                streaming=True,
            )
        return self._model_cache[spec.model_id]

    def _detect_images(self, messages: Sequence[BaseMessage]) -> bool:
        """Check if messages contain image content."""
        for msg in messages:
            content = msg.content
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        return True
        return False

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response by routing to the optimal model."""
        self._metrics["total_requests"] += 1

        # Classify request
        has_images = self._detect_images(messages)
        task_type, confidence = self._classifier.classify(messages, has_images)

        # Update metrics
        self._metrics["by_task_type"][task_type.value] = \
            self._metrics["by_task_type"].get(task_type.value, 0) + 1

        # Get models to try
        primary_spec = get_model_for_task(task_type)
        fallback_specs = get_fallback_models(primary_spec.model_id, has_images)
        models_to_try = [primary_spec] + fallback_specs

        logger.info(f"[Router] Task: {task_type.value} (confidence: {confidence:.2f})")
        logger.info(f"[Router] Primary model: {primary_spec.display_name}")

        last_error = None
        used_fallback = False

        for i, spec in enumerate(models_to_try):
            try:
                model = self._get_model(spec)
                result = model._generate(messages, stop, run_manager, **kwargs)

                # Track model usage
                self._metrics["by_model"][spec.model_id] = \
                    self._metrics["by_model"].get(spec.model_id, 0) + 1

                if used_fallback:
                    self._metrics["fallback_count"] += 1

                return result

            except Exception as e:
                last_error = e
                used_fallback = True
                error_str = str(e)

                # Track errors
                self._metrics["errors"][spec.model_id] = \
                    self._metrics["errors"].get(spec.model_id, 0) + 1

                # Check if we should retry with fallback
                if "429" in error_str or "rate" in error_str.lower():
                    logger.warning(f"[Router] Rate limited on {spec.display_name}, trying fallback...")
                    continue
                elif "500" in error_str or "502" in error_str or "503" in error_str:
                    logger.warning(f"[Router] Server error on {spec.display_name}, trying fallback...")
                    continue
                else:
                    # For other errors, still try fallback but log it
                    logger.error(f"[Router] Error on {spec.display_name}: {e}")
                    if i < len(models_to_try) - 1:
                        continue
                    raise

        # All models failed
        raise RuntimeError(f"All models failed. Last error: {last_error}")

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream a response by routing to the optimal model."""
        self._metrics["total_requests"] += 1

        # Classify request
        has_images = self._detect_images(messages)
        task_type, confidence = self._classifier.classify(messages, has_images)

        # Update metrics
        self._metrics["by_task_type"][task_type.value] = \
            self._metrics["by_task_type"].get(task_type.value, 0) + 1

        # Get models to try
        primary_spec = get_model_for_task(task_type)
        fallback_specs = get_fallback_models(primary_spec.model_id, has_images)
        models_to_try = [primary_spec] + fallback_specs

        logger.info(f"[Router] Task: {task_type.value} (confidence: {confidence:.2f})")
        logger.info(f"[Router] Primary model: {primary_spec.display_name}")

        last_error = None
        used_fallback = False

        for i, spec in enumerate(models_to_try):
            try:
                model = self._get_model(spec)

                # Track model usage
                self._metrics["by_model"][spec.model_id] = \
                    self._metrics["by_model"].get(spec.model_id, 0) + 1

                if used_fallback:
                    self._metrics["fallback_count"] += 1

                # Stream from the model
                for chunk in model._stream(messages, stop, run_manager, **kwargs):
                    yield chunk

                return

            except Exception as e:
                last_error = e
                used_fallback = True
                error_str = str(e)

                # Track errors
                self._metrics["errors"][spec.model_id] = \
                    self._metrics["errors"].get(spec.model_id, 0) + 1

                if "429" in error_str or "rate" in error_str.lower():
                    logger.warning(f"[Router] Rate limited on {spec.display_name}, trying fallback...")
                    continue
                elif "500" in error_str or "502" in error_str or "503" in error_str:
                    logger.warning(f"[Router] Server error on {spec.display_name}, trying fallback...")
                    continue
                else:
                    logger.error(f"[Router] Error on {spec.display_name}: {e}")
                    if i < len(models_to_try) - 1:
                        continue
                    raise

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    def get_metrics(self) -> dict:
        """Get routing metrics."""
        return {
            **self._metrics,
            "fallback_rate": self._metrics["fallback_count"] / max(self._metrics["total_requests"], 1),
        }

    def bind_tools(self, tools: List[Any], **kwargs: Any) -> "CompositeRoutingChatModel":
        """Bind tools - delegates to underlying models."""
        # For tool binding, we need to ensure all cached models have tools bound
        # This is a simplified implementation; in practice you might want to
        # create a new instance with tools pre-bound
        return self
```

### FR-4: Updated Agent Creation

```python
# baseline-langchain/janus_baseline_langchain/agent.py

"""LangChain agent setup with composite model routing."""

from typing import Any, cast

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.tools import (
    code_execution_tool,
    image_generation_tool,
    text_to_speech_tool,
    web_search_tool,
)

SYSTEM_PROMPT = """You are Janus, an intelligent assistant competing in The Rodeo.

You have access to these tools:
- image_generation: Generate images using AI (Chutes API)
- text_to_speech: Convert text to audio (Kokoro TTS)
- web_search: Search the web for current information
- code_execution: Execute Python code safely

Always use the appropriate tool for the task. For image requests, use image_generation.
For audio/speech requests, use text_to_speech.
For questions about current events or real-time data, use web_search.
For calculations or data processing, use code_execution.
"""


def create_agent(settings: Settings) -> AgentExecutor:
    """Create a LangChain agent executor with composite model routing."""

    # Use composite routing model if enabled
    if settings.use_model_router:
        llm = CompositeRoutingChatModel(
            api_key=settings.chutes_api_key or settings.openai_api_key or "",
            base_url=settings.openai_base_url,
            default_temperature=settings.temperature,
        )
    else:
        # Fall back to single model (original behavior)
        from langchain_openai import ChatOpenAI
        from pydantic.v1 import SecretStr

        api_key = (
            SecretStr(settings.openai_api_key)
            if settings.openai_api_key
            else SecretStr("dummy-key")
        )
        llm = ChatOpenAI(
            model=settings.model,
            api_key=api_key,
            base_url=settings.openai_base_url,
            temperature=settings.temperature,
            streaming=True,
            max_retries=settings.max_retries,
            timeout=settings.request_timeout,
        )

    tools = [
        image_generation_tool,
        text_to_speech_tool,
        web_search_tool,
        code_execution_tool,
    ]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=cast(Any, agent),
        tools=tools,
        verbose=settings.debug,
        max_iterations=10,
        return_intermediate_steps=True,
    )
```

### FR-5: Configuration Updates

```python
# baseline-langchain/janus_baseline_langchain/config.py

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Baseline LangChain configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BASELINE_LANGCHAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8002, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Model Router settings (NEW)
    use_model_router: bool = Field(
        default=True,
        description="Enable composite model routing",
    )

    # LLM settings (used when router disabled)
    model: str = Field(default="zai-org/GLM-4.7-TEE", description="Default model")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://llm.chutes.ai/v1",
        description="OpenAI-compatible base URL",
    )
    temperature: float = Field(default=0.7, description="Model temperature")

    # Vision settings (used by router for vision tasks)
    vision_model_primary: str = Field(
        default="Qwen/Qwen3-VL-235B-A22B-Instruct",
        validation_alias=AliasChoices(
            "BASELINE_VISION_MODEL_PRIMARY",
            "BASELINE_LANGCHAIN_VISION_MODEL_PRIMARY",
        ),
        description="Primary vision model for image understanding",
    )
    vision_model_fallback: str = Field(
        default="zai-org/GLM-4.6V",
        validation_alias=AliasChoices(
            "BASELINE_VISION_MODEL_FALLBACK",
            "BASELINE_LANGCHAIN_VISION_MODEL_FALLBACK",
        ),
        description="Fallback vision model for image understanding",
    )

    # Chutes settings
    chutes_api_key: Optional[str] = Field(
        default=None, description="Chutes API key for all services"
    )

    # Web search
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")

    # HTTP behavior
    request_timeout: float = Field(default=30.0, description="HTTP request timeout")
    max_retries: int = Field(default=2, description="Max retries for external APIs")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### FR-6: Metrics Endpoint

```python
# baseline-langchain/janus_baseline_langchain/main.py

# Add to existing FastAPI app

from fastapi import FastAPI

app = FastAPI(title="Janus Baseline (LangChain)", version="1.0.0")

# Store agent reference for metrics
_agent_executor = None


@app.on_event("startup")
async def startup():
    global _agent_executor
    settings = get_settings()
    _agent_executor = create_agent(settings)


@app.get("/v1/router/metrics")
async def get_router_metrics():
    """Get composite model router metrics."""
    if _agent_executor is None:
        return {"error": "Agent not initialized"}

    # Access the LLM from the agent
    agent = _agent_executor.agent
    if hasattr(agent, "llm") and hasattr(agent.llm, "get_metrics"):
        return agent.llm.get_metrics()

    return {"error": "Router metrics not available"}
```

### FR-7: Alternative: Using LangChain's RunnableRouter

For more complex routing logic, LangChain provides `RunnableRouter`:

```python
# baseline-langchain/janus_baseline_langchain/router/runnable_router.py

from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.runnables.router import RouterRunnable
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from .models import TaskType, MODEL_SPECS, get_model_for_task
from .classifier import TaskClassifier


def create_routing_chain(api_key: str, base_url: str = "https://llm.chutes.ai/v1"):
    """
    Create a LangChain routing chain using RunnableRouter.

    This is an alternative approach that uses LangChain's built-in
    routing primitives for more complex conditional logic.
    """
    classifier = TaskClassifier(api_key, base_url)

    # Create model instances
    models = {}
    for key, spec in MODEL_SPECS.items():
        if key != "classifier":
            models[spec.model_id] = ChatOpenAI(
                model=spec.model_id,
                api_key=SecretStr(api_key),
                base_url=base_url,
                temperature=spec.temperature,
                max_tokens=spec.max_tokens,
                timeout=spec.timeout_seconds,
                streaming=True,
            )

    def route_to_model(input_dict: dict) -> str:
        """Determine which model to route to."""
        messages = input_dict.get("messages", [])
        has_images = any(
            isinstance(m.content, list) and
            any(p.get("type") == "image_url" for p in m.content if isinstance(p, dict))
            for m in messages
        )

        task_type, _ = classifier.classify(messages, has_images)
        spec = get_model_for_task(task_type)
        return spec.model_id

    # Create router
    router = RouterRunnable(
        runnables=models,
        router_func=route_to_model,
    )

    return router
```

## Comparison: Native vs Proxy Approach

| Aspect | Native (This Spec) | Proxy (Spec 58) |
|--------|-------------------|-----------------|
| Architecture | Single process | Two processes |
| Complexity | Higher (custom ChatModel) | Lower (HTTP proxy) |
| Latency | Lower (no HTTP hop) | Higher (~10-20ms) |
| Debugging | Integrated logging | Separate logs |
| LangChain Integration | Native callbacks | Limited |
| Streaming | Native support | HTTP SSE proxy |
| Reusability | LangChain only | Any OpenAI client |

**Recommendation**: Use the native approach for baseline-langchain since it provides better integration with LangChain's ecosystem.

## Non-Functional Requirements

### NFR-1: Latency
- Classification overhead: < 150ms average (no HTTP hop)
- First token latency impact: < 200ms

### NFR-2: Reliability
- 99.9% availability with fallbacks
- Graceful degradation
- Proper error propagation

### NFR-3: Observability
- LangChain callback integration
- Metrics endpoint
- Structured logging

## Acceptance Criteria

- [ ] `CompositeRoutingChatModel` implements `BaseChatModel`
- [ ] Classification correctly identifies task types
- [ ] Vision requests route to vision models
- [ ] Programming requests route to MiniMax
- [ ] Math requests route to DeepSeek V3.2
- [ ] Creative requests route to TNG R1T2
- [ ] Fallback works on 429/5xx errors
- [ ] Streaming works through router
- [ ] Agent executor works with routing model
- [ ] Metrics endpoint returns data
- [ ] Tests pass

## Files to Create

```
baseline-langchain/
├── janus_baseline_langchain/
│   └── router/
│       ├── __init__.py
│       ├── models.py           # Model registry (shared logic)
│       ├── classifier.py       # Task classifier
│       ├── chat_model.py       # CompositeRoutingChatModel
│       └── runnable_router.py  # Alternative RunnableRouter approach
├── tests/
│   ├── test_router.py
│   └── test_classifier.py
└── config.py                   # MODIFY
└── agent.py                    # MODIFY
└── main.py                     # MODIFY
```

## Related Specs

- `specs/58_composite_model_router.md` - CLI baseline router (proxy approach)
- `specs/38_multimodal_vision_models.md` - Vision model support
- `specs/27_baseline_langchain.md` - Original LangChain baseline spec

## References

- [LangChain Custom Chat Models](https://python.langchain.com/docs/how_to/custom_chat_model/)
- [LangChain Routing](https://python.langchain.com/docs/how_to/routing/)
- [LangChain Callbacks](https://python.langchain.com/docs/concepts/callbacks/)
