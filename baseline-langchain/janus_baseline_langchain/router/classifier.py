"""LLM-based task classifier for routing decisions."""

from __future__ import annotations

import logging
from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from janus_baseline_langchain.router.models import MODEL_REGISTRY, TaskType

logger = logging.getLogger(__name__)

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
                        "enum": [t.value for t in TaskType if t != TaskType.UNKNOWN],
                        "description": "The classified task type",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score (0-1)",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief explanation of classification",
                    },
                },
                "required": ["task_type", "confidence"],
            },
        },
    }
]

COMPLEX_KEYWORDS = [
    "write",
    "create",
    "implement",
    "code",
    "function",
    "class",
    "prove",
    "solve",
    "calculate",
    "equation",
    "story",
    "roleplay",
    "explain",
    "analyze",
    "compare",
    "design",
    "build",
]


class TaskClassifier:
    """Classifies incoming requests using a fast LLM."""

    def __init__(self, api_key: str, base_url: str = "https://llm.chutes.ai/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url
        self._llm: ChatOpenAI | None = None

    @property
    def classifier_llm(self) -> ChatOpenAI:
        """Lazily initialize the classifier LLM."""
        if self._llm is None:
            model_config = MODEL_REGISTRY["classifier"]
            self._llm = ChatOpenAI(
                model=model_config.model_id,
                api_key=SecretStr(self.api_key),
                base_url=self.base_url,
                temperature=model_config.temperature,
                max_tokens=100,
                timeout=model_config.timeout_seconds,
            )
        return self._llm

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
        if has_images:
            return TaskType.VISION, 1.0

        user_content = self._extract_user_content(messages)

        if len(user_content) < 50 and not self._has_complex_keywords(user_content):
            return TaskType.SIMPLE_TEXT, 0.8

        try:
            response = self.classifier_llm.invoke(
                [
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": f"Classify: {user_content[:2000]}"},
                ],
                tools=CLASSIFICATION_TOOLS,
                tool_choice={"type": "function", "function": {"name": "classify_task"}},
            )

            if response.tool_calls:
                args = response.tool_calls[0]["args"]
                task_type = TaskType(args["task_type"])
                confidence = args.get("confidence", 0.7)
                logger.info(
                    f"[Classifier] Task: {task_type.value}, confidence: {confidence}"
                )
                return task_type, confidence

        except Exception as e:
            logger.warning(f"[Classifier] Error: {e}")

        return TaskType.GENERAL_TEXT, 0.5

    def _extract_user_content(self, messages: Sequence[BaseMessage]) -> str:
        """Extract text from user messages."""
        parts: list[str] = []
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
        text_lower = text.lower()
        return any(kw in text_lower for kw in COMPLEX_KEYWORDS)
