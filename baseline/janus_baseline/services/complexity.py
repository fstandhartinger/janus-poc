"""Complexity detection service to route between fast and complex paths."""

import re
from functools import lru_cache
from typing import Optional

from janus_baseline.config import Settings, get_settings
from janus_baseline.models import Message, MessageContent


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

    def _has_complex_keywords(self, text: str) -> bool:
        """Check if text contains keywords suggesting complexity."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.COMPLEX_KEYWORDS)

    def _has_code_blocks(self, text: str) -> bool:
        """Check if text contains code blocks."""
        return "```" in text

    def is_complex(self, messages: list[Message]) -> tuple[bool, str]:
        """
        Determine if the request is complex and needs sandbox execution.

        Returns:
            Tuple of (is_complex, reason)
        """
        if not messages:
            return False, "empty_messages"

        # Get the last user message
        last_user_msg = None
        for msg in reversed(messages):
            if msg.role.value == "user":
                last_user_msg = msg
                break

        if not last_user_msg:
            return False, "no_user_message"

        text = self._extract_text(last_user_msg.content)

        # Check for complex keywords
        if self._has_complex_keywords(text):
            return True, "complex_keywords"

        # Check for code blocks in context (suggesting code-related task)
        all_text = " ".join(self._extract_text(m.content) for m in messages)
        if self._has_code_blocks(all_text) and self._has_complex_keywords(text):
            return True, "code_context"

        # Check token length
        total_tokens = sum(self._estimate_tokens(self._extract_text(m.content)) for m in messages)
        if total_tokens > self._threshold:
            return True, "token_threshold"

        return False, "simple"


@lru_cache
def get_complexity_detector() -> ComplexityDetector:
    """Get cached complexity detector instance."""
    return ComplexityDetector(get_settings())
