"""Complexity detection service to route between fast and complex paths."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from janus_baseline.config import Settings, get_settings
from janus_baseline.models import Message, MessageContent


@dataclass(frozen=True)
class ComplexityAnalysis:
    """Analysis result for complexity detection."""

    is_complex: bool
    reason: str
    keywords_matched: list[str]
    multimodal_detected: bool
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
        self._threshold = settings.complexity_threshold

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

    def analyze(self, messages: list[Message]) -> ComplexityAnalysis:
        """Analyze the request for complexity routing."""
        if not messages:
            return ComplexityAnalysis(
                is_complex=False,
                reason="empty_messages",
                keywords_matched=[],
                multimodal_detected=False,
                text_preview="",
            )

        # Get the last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.role.value == "user":
                last_user_msg = msg
                break

        if not last_user_msg:
            return ComplexityAnalysis(
                is_complex=False,
                reason="no_user_message",
                keywords_matched=[],
                multimodal_detected=False,
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
                text_preview=text_preview,
            )

        # Check for complex keywords
        if keywords_matched:
            return ComplexityAnalysis(
                is_complex=True,
                reason="complex_keywords",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
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
                text_preview=text_preview,
            )

        # Check token length
        total_tokens = sum(self._estimate_tokens(self._extract_text(m.content)) for m in messages)
        if total_tokens > self._threshold:
            return ComplexityAnalysis(
                is_complex=True,
                reason="token_threshold",
                keywords_matched=keywords_matched,
                multimodal_detected=multimodal_detected,
                text_preview=text_preview,
            )

        return ComplexityAnalysis(
            is_complex=False,
            reason="simple",
            keywords_matched=keywords_matched,
            multimodal_detected=multimodal_detected,
            text_preview=text_preview,
        )

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
