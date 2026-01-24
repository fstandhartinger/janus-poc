"""Complexity detection service to route between fast and complex paths."""

from dataclasses import dataclass
from functools import lru_cache
import json
from typing import Optional

import httpx
import structlog

from janus_baseline_agent_cli.config import Settings, get_settings
from janus_baseline_agent_cli.models import Message, MessageContent
from janus_baseline_agent_cli.services.vision import contains_images, count_images

logger = structlog.get_logger()

ROUTING_ENDPOINT = "https://llm.chutes.ai/v1/chat/completions"
ROUTING_MODEL = "zai-org/GLM-4.7-Flash"
ROUTING_PROMPT = """Analyze this user request and decide if it needs agent sandbox capabilities.

Agent sandbox is needed for:
- Image/video/audio generation (e.g., "generate an image of...", "create a video...")
- Code execution (e.g., "run this code", "execute...")
- Web search (e.g., "search for...", "find current...")
- File operations (e.g., "download...", "save to file...")
- Any task requiring external tools or APIs

Direct LLM response is sufficient for:
- General conversation and questions
- Explanations and summaries
- Simple math (without code)
- Writing assistance (without execution)

User request: {user_message}

Call the use_agent function with your decision."""

USE_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "use_agent",
        "description": (
            "Decide whether this request needs the agent sandbox with tools (for image "
            "generation, code execution, web search, etc.) or can be answered directly by LLM."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "needs_agent": {
                    "type": "boolean",
                    "description": (
                        "True if request needs agent sandbox (image gen, code exec, web search, "
                        "file ops). False if LLM can answer directly."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of the decision",
                },
            },
            "required": ["needs_agent", "reason"],
            "additionalProperties": False,
        },
    },
}

TRIVIAL_GREETINGS = {
    "hello",
    "hi",
    "hey",
    "hi there",
    "hello there",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
}


@dataclass(frozen=True)
class ComplexityAnalysis:
    """Analysis result for complexity detection."""

    is_complex: bool
    reason: str
    keywords_matched: list[str]
    multimodal_detected: bool
    has_images: bool
    image_count: int
    text_preview: str


class ComplexityDetector:
    """Detects whether a request should use the fast path or complex path."""

    # Keywords that suggest a complex task requiring sandbox
    COMPLEX_KEYWORDS = [
        "write code",
        "create a file",
        "build",
        "implement",
        "develop",
        "debug",
        "fix the bug",
        "refactor",
        "run tests",
        "execute",
        "compile",
        "deploy",
        "install",
        "analyze this codebase",
        "modify the",
        "update the code",
        "create a script",
        "write a program",
        "generate code",
        "generate image",
        "generate an image",
        "create image",
        "create an image",
        "create picture",
        "draw",
        "make a picture",
        "image of",
        "picture of",
        "illustration of",
        "photo of",
        "render",
        "text to speech",
        "generate audio",
        "create audio",
        "speak this",
        "say this",
        "read aloud",
        "voice",
        "tts",
        "generate video",
        "create video",
        "make a video",
        "animate",
        "animation",
        "search the web",
        "search online",
        "research",
        "find information",
        "look up",
        "what is the latest",
        "current news",
        "recent developments",
        "download",
        "fetch",
        "scrape",
        "extract data",
        "parse",
        "convert file",
    ]

    MULTIMODAL_KEYWORDS = [
        "image",
        "picture",
        "photo",
        "illustration",
        "draw",
        "render",
        "audio",
        "voice",
        "speech",
        "sound",
        "speak",
        "tts",
        "video",
        "animate",
        "animation",
        "clip",
    ]

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._threshold = settings.complexity_threshold
        self._routing_model = settings.llm_routing_model or ROUTING_MODEL
        self._routing_timeout = settings.llm_routing_timeout

    def _get_last_user_message(self, messages: list[Message]) -> Optional[Message]:
        """Get the most recent user message from the list."""
        for msg in reversed(messages):
            if msg.role.value == "user":
                return msg
        return None

    def _normalize_text(self, text: str) -> str:
        cleaned = "".join(
            ch for ch in text.lower() if ch.isalnum() or ch.isspace()
        ).strip()
        return " ".join(cleaned.split())

    def _should_skip_llm_check(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        return not normalized or normalized in TRIVIAL_GREETINGS

    def _extract_text(self, content: Optional[MessageContent]) -> str:
        """Extract text from message content."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        text_parts = []
        for part in content:
            if hasattr(part, "text"):
                text_parts.append(part.text)
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return " ".join(text_parts)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (words * 1.3)."""
        words = len(text.split())
        return int(words * 1.3)

    def _matched_complex_keywords(self, text: str) -> list[str]:
        """Return complex keywords found in text."""
        text_lower = text.lower()
        return [keyword for keyword in self.COMPLEX_KEYWORDS if keyword in text_lower]

    def _has_complex_keywords(self, text: str) -> bool:
        """Check if text contains keywords suggesting complexity."""
        return bool(self._matched_complex_keywords(text))

    def _has_code_blocks(self, text: str) -> bool:
        """Check if text contains code blocks."""
        return "```" in text

    def _is_multimodal_request(self, text: str) -> bool:
        """Check if request involves multimodal generation."""
        text_lower = text.lower()
        generation_verbs = ["generate", "create", "make", "produce", "render"]

        for verb in generation_verbs:
            if verb not in text_lower:
                continue
            for media in self.MULTIMODAL_KEYWORDS:
                if media in text_lower:
                    return True

        return False

    def _needs_agent_for_images(self, text: str) -> bool:
        """Check if image analysis requires tools beyond vision."""
        agent_triggers = [
            "search for",
            "find more",
            "look up",
            "write code",
            "execute",
            "run this",
            "compare with",
            "fetch",
            "download",
        ]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in agent_triggers)

    def analyze(self, messages: list[Message]) -> ComplexityAnalysis:
        """Analyze the request for complexity routing."""
        if not messages:
            return ComplexityAnalysis(
                is_complex=False,
                reason="empty_messages",
                keywords_matched=[],
                multimodal_detected=False,
                has_images=False,
                image_count=0,
                text_preview="",
            )

        has_images = contains_images(messages)
        image_count = count_images(messages) if has_images else 0

        # Get the last user message
        last_user_msg = self._get_last_user_message(messages)

        if not last_user_msg:
            return ComplexityAnalysis(
                is_complex=False,
                reason="no_user_message",
                keywords_matched=[],
                multimodal_detected=False,
                has_images=has_images,
                image_count=image_count,
                text_preview="",
            )

        text = self._extract_text(last_user_msg.content)
        keywords_matched = self._matched_complex_keywords(text)
        multimodal_detected = self._is_multimodal_request(text)
        text_preview = text[:100]

        # Check for multimodal request
        if multimodal_detected:
            return ComplexityAnalysis(
                is_complex=True,
                reason="multimodal_request",
                keywords_matched=keywords_matched,
                multimodal_detected=True,
                has_images=has_images,
                image_count=image_count,
                text_preview=text_preview,
            )

        # Check for complex keywords
        if keywords_matched:
            return ComplexityAnalysis(
                is_complex=True,
                reason="complex_keywords",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
                has_images=has_images,
                image_count=image_count,
                text_preview=text_preview,
            )

        # Check for code blocks in context (suggesting code-related task)
        all_text = " ".join(self._extract_text(m.content) for m in messages)
        if self._has_code_blocks(all_text) and self._has_complex_keywords(text):
            return ComplexityAnalysis(
                is_complex=True,
                reason="code_context",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
                has_images=has_images,
                image_count=image_count,
                text_preview=text_preview,
            )

        # Check token length
        total_tokens = sum(self._estimate_tokens(self._extract_text(m.content)) for m in messages)
        if has_images and self._needs_agent_for_images(text):
            return ComplexityAnalysis(
                is_complex=True,
                reason="image_with_tools",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
                has_images=has_images,
                image_count=image_count,
                text_preview=text_preview,
            )

        if total_tokens > self._threshold:
            return ComplexityAnalysis(
                is_complex=True,
                reason="token_threshold",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
                has_images=has_images,
                image_count=image_count,
                text_preview=text_preview,
            )

        return ComplexityAnalysis(
            is_complex=False,
            reason="simple",
            keywords_matched=keywords_matched,
            multimodal_detected=multimodal_detected,
            has_images=has_images,
            image_count=image_count,
            text_preview=text_preview,
        )

    async def _llm_routing_check(self, text: str) -> tuple[bool, str]:
        """Second pass: Use LLM with tool calling to verify routing decision."""
        if not self._settings.openai_api_key:
            return False, "no_api_key"

        try:
            async with httpx.AsyncClient(timeout=self._routing_timeout) as client:
                response = await client.post(
                    ROUTING_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self._settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._routing_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": ROUTING_PROMPT.format(user_message=text[:500]),
                            }
                        ],
                        "tools": [USE_AGENT_TOOL],
                        "tool_choice": {
                            "type": "function",
                            "function": {"name": "use_agent"},
                        },
                        "max_tokens": 100,
                        "temperature": 0.0,
                    },
                )
                response.raise_for_status()
                data = response.json()

                message = data["choices"][0]["message"]
                tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
                if tool_calls:
                    tool_call = tool_calls[0]
                    arguments = tool_call.get("function", {}).get("arguments", "{}")
                    if isinstance(arguments, dict):
                        args = arguments
                    else:
                        args = json.loads(arguments)
                    return bool(args.get("needs_agent", False)), str(
                        args.get("reason", "llm_decision")
                    )

                return False, "no_tool_call"

        except Exception as exc:
            logger.warning(
                "llm_routing_error",
                error=str(exc),
                text_preview=text[:100],
            )
            return False, f"llm_check_error: {exc}"

    async def analyze_async(self, messages: list[Message]) -> ComplexityAnalysis:
        """Async version of analyze with optional LLM second pass."""
        # First pass: keyword-based (same as before)
        first_pass = self.analyze(messages)

        # If already complex, no need for second pass
        if first_pass.is_complex:
            return first_pass

        # Second pass only if enabled and first pass said "simple"
        if self._settings.enable_llm_routing:
            last_user_msg = self._get_last_user_message(messages)
            text = self._extract_text(last_user_msg.content) if last_user_msg else ""
            if not self._should_skip_llm_check(text):
                needs_agent, reason = await self._llm_routing_check(text)
                logger.info(
                    "llm_routing_decision",
                    needs_agent=needs_agent,
                    reason=reason,
                    model=self._routing_model,
                    text_preview=text[:100],
                )

                if needs_agent:
                    return ComplexityAnalysis(
                        is_complex=True,
                        reason=f"llm_second_pass: {reason}",
                        keywords_matched=first_pass.keywords_matched,
                        multimodal_detected=first_pass.multimodal_detected,
                        has_images=first_pass.has_images,
                        image_count=first_pass.image_count,
                        text_preview=first_pass.text_preview,
                    )

        return first_pass

    def is_complex(self, messages: list[Message]) -> tuple[bool, str]:
        """
        Determine if the request is complex and needs sandbox execution.

        Returns:
            Tuple of (is_complex, reason)
        """
        analysis = self.analyze(messages)
        return analysis.is_complex, analysis.reason


@lru_cache
def get_complexity_detector() -> ComplexityDetector:
    """Get cached complexity detector instance."""
    return ComplexityDetector(get_settings())
