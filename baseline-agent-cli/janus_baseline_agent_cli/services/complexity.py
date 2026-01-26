"""Complexity detection service to route between fast and complex paths."""

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Optional

import httpx
import structlog

from janus_baseline_agent_cli.config import Settings, get_settings
from janus_baseline_agent_cli.logging import log_function_call
from janus_baseline_agent_cli.models import GenerationFlags, Message, MessageContent
from janus_baseline_agent_cli.tools.parser import robust_parse_tool_call
from janus_baseline_agent_cli.services.vision import contains_images, count_images

logger = structlog.get_logger()

ROUTING_ENDPOINT = "https://llm.chutes.ai/v1/chat/completions"

# Routing models in order of preference (with fallbacks)
ROUTING_MODELS = [
    "XiaomiMiMo/MiMo-V2-Flash",  # Fast, reliable
    "deepseek-ai/DeepSeek-V3",    # Fallback
    "zai-org/GLM-4.7-TEE",        # Second fallback
]
ROUTING_MODEL = ROUTING_MODELS[0]  # Default for settings
ROUTING_PROMPT = """Analyze this user request and decide if it needs agent sandbox capabilities.

Agent sandbox is REQUIRED for:
- Image/video/audio generation ("generate an image", "create a video", "text to speech")
- Code execution ("run this code", "execute", "test this script" or queries that are best answered by writing/running code)
- Web search ("search for", "find current", "latest news")
- File operations ("download", "save to file", "read file")
- Browser automation ("test in browser", "open URL", "take screenshot", "click on")
- GUI/Desktop interaction ("click button", "type into", "automate")
- API calls ("call the API", "make a request", "curl")
- Testing ("run tests", "verify", "check if working")
- Any task requiring interaction with external systems, URLs, or tools

Direct LLM response is ONLY sufficient for:
- General conversation and chitchat
- Explanations, definitions, and summaries that don't require up-to-date information or context from the internet
- Simple math (without needing to run code)
- Writing assistance (text generation without execution)
- Questions that can be answered from knowledge alone (and where there is no need to look up the latest information or context from the internet)

IMPORTANT: When in doubt, choose needs_agent=true. It's better to use the agent unnecessarily than to fail a task that needs tools.

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
    "ok",
    "okay",
    "yes",
    "no",
    "sure",
    "bye",
    "goodbye",
    "see you",
    "later",
    "whats up",
    "what up",
    "howdy",
    "yo",
    "hola",
    "hallo",
    "guten tag",
    "guten morgen",
    "guten abend",
    "danke",
    "bitte",
    "tschuss",
    "ciao",
}

# Patterns for simple conversational requests that don't need agent
SIMPLE_CONVERSATION_PATTERNS = [
    r"^(say|just say|respond with)\s+(hi|hello|hey)\s*$",
    r"^(tell me|say)\s+a\s+(joke|riddle)\s*$",
    r"^what\s+is\s+\d+\s*[\+\-\*\/]\s*\d+\s*\??$",  # Simple math
    r"^how\s+are\s+you\s*\??$",
    r"^what\s+do\s+you\s+think\s*\??$",
    r"^who\s+are\s+you\s*\??$",
    r"^what\s+is\s+your\s+name\s*\??$",
    r"^(can|could)\s+you\s+help\s+me\s*\??$",
    r"^(please\s+)?(explain|define|what\s+is)\s+[a-z\s]+\s*\??$",
]

URL_PATTERN = re.compile(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', re.IGNORECASE)


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

    COMPLEX_KEYWORDS_DE = [
        # Download/Fetch
        "herunterladen",
        "lade herunter",
        "downloaden",
        "holen",
        # Search
        "suche",
        "such nach",
        "recherchiere",
        "finde",
        "finde heraus",
        # Code execution
        "führe aus",
        "ausführen",
        "starte",
        "kompiliere",
        "teste",
        "debugge",
        # File operations
        "speichere",
        "schreibe",
        "erstelle datei",
        "lösche",
        # Web/Browser
        "öffne",
        "besuche",
        "navigiere",
        "screenshot",
        # Generation
        "generiere",
        "erstelle bild",
        "erzeuge",
        "zusammenfassung",
        "analysiere",
    ]

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
        "test in browser",
        "test in a browser",
        "open in browser",
        "browser automation",
        "playwright",
        "puppeteer",
        "selenium",
        "click on",
        "navigate to",
        "take screenshot",
        "screenshot of",
        "load the page",
        "open the url",
        "open this url",
        "visit the site",
        "visit this site",
        "check the website",
        "test the website",
        "verify the page",
        "interact with",
        "fill the form",
        "submit the form",
        "automation",
        "automate",
        "gui",
        "desktop automation",
        "click the button",
        "type into",
        "keyboard",
        "mouse click",
        "run the test",
        "test this",
        "verify this",
        "check if",
        "validate",
        "smoke test",
        "integration test",
        "e2e test",
        "end-to-end",
        "call the api",
        "make a request",
        "http request",
        "curl",
        "post to",
        "get from",
        "api endpoint",
        "run command",
        "execute command",
        "terminal",
        "shell",
        "bash",
        "command line",
        # Git/Repository operations
        "git clone",
        "git pull",
        "git push",
        "github",
        "gitlab",
        "repository",
        "repo",
        "clone the",
        "pull the repo",
        "clone repo",
        # German keywords
        *COMPLEX_KEYWORDS_DE,
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
        if not normalized:
            return True
        if normalized in TRIVIAL_GREETINGS:
            return True
        # Check simple conversation patterns
        for pattern in SIMPLE_CONVERSATION_PATTERNS:
            if re.match(pattern, normalized, re.IGNORECASE):
                return True
        return False

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

    # German separable verb patterns: "lade ... herunter" -> "herunterladen"
    GERMAN_SEPARABLE_VERBS = [
        (r"lade\s+.+\s+herunter", "herunterladen"),
        (r"such(e)?\s+.+\s+nach", "suchen nach"),
        (r"führ(e)?\s+.+\s+aus", "ausführen"),
        (r"stell(e)?\s+.+\s+ein", "einstellen"),
        (r"gib\s+.+\s+zusammenfassung", "zusammenfassung"),
        (r"fass\s+.+\s+zusammen", "zusammenfassung"),
    ]

    def _matched_complex_keywords(self, text: str) -> list[str]:
        """Return complex keywords found in text."""
        text_lower = text.lower()
        matches = [keyword for keyword in self.COMPLEX_KEYWORDS if keyword in text_lower]

        # Also check German separable verb patterns
        for pattern, keyword in self.GERMAN_SEPARABLE_VERBS:
            if re.search(pattern, text_lower):
                matches.append(keyword)

        return matches

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

    def _contains_url(self, text: str) -> bool:
        """Check if text contains a URL."""
        return bool(URL_PATTERN.search(text))

    def _url_suggests_interaction(self, text: str) -> bool:
        """Check if URL context suggests browser/API interaction."""
        if not self._contains_url(text):
            return False

        interaction_hints = [
            "test",
            "check",
            "visit",
            "open",
            "browse",
            "verify",
            "screenshot",
            "load",
            "fetch",
            "scrape",
            "interact",
            "click",
            "submit",
            "form",
            "login",
            "api",
            "endpoint",
        ]
        text_lower = text.lower()
        return any(hint in text_lower for hint in interaction_hints)

    def _flag_reasons(self, flags: GenerationFlags) -> list[str]:
        reasons: list[str] = []
        if flags.generate_image:
            reasons.append("image generation requested")
        if flags.generate_video:
            reasons.append("video generation requested")
        if flags.generate_audio:
            reasons.append("audio generation requested")
        if flags.deep_research:
            reasons.append("deep research requested")
        if flags.web_search:
            reasons.append("web search requested")
        return reasons

    def analyze(
        self,
        messages: list[Message],
        flags: GenerationFlags | None = None,
    ) -> ComplexityAnalysis:
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

        if flags:
            flag_reasons = self._flag_reasons(flags)
            if flag_reasons:
                return ComplexityAnalysis(
                    is_complex=True,
                    reason=f"generation_flags: {', '.join(flag_reasons)}",
                    keywords_matched=flag_reasons,
                    multimodal_detected=False,
                    has_images=has_images,
                    image_count=image_count,
                    text_preview=text_preview,
                )

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

        if self._url_suggests_interaction(text):
            return ComplexityAnalysis(
                is_complex=True,
                reason="url_interaction",
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

    async def _try_routing_model(
        self, client: httpx.AsyncClient, model: str, text: str
    ) -> tuple[bool, str, bool]:
        """Try routing with a specific model. Returns (needs_agent, reason, success)."""
        try:
            response = await client.post(
                ROUTING_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self._settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
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
                args = robust_parse_tool_call(arguments)
                return bool(args.get("needs_agent", False)), str(
                    args.get("reason", "llm_decision")
                ), True

            return True, "no_tool_call_conservative", True

        except httpx.TimeoutException:
            logger.warning("llm_routing_timeout", model=model, text_preview=text[:100])
            return True, f"timeout ({model})", False

        except Exception as exc:
            logger.warning(
                "llm_routing_error",
                model=model,
                error=str(exc),
                text_preview=text[:100],
            )
            return True, str(exc), False

    @log_function_call
    async def _llm_routing_check(self, text: str) -> tuple[bool, str]:
        """LLM verification for routing decision with fallback models."""
        if not self._settings.openai_api_key:
            return True, "no_api_key"

        # Try each model in order until one succeeds
        models_to_try = [self._routing_model] + [
            m for m in ROUTING_MODELS if m != self._routing_model
        ]

        async with httpx.AsyncClient(timeout=self._routing_timeout) as client:
            for model in models_to_try:
                needs_agent, reason, success = await self._try_routing_model(
                    client, model, text
                )
                if success:
                    logger.info(
                        "llm_routing_success",
                        model=model,
                        needs_agent=needs_agent,
                        reason=reason,
                    )
                    return needs_agent, reason

        # All models failed
        return True, "llm_check_error: all models unavailable"

    @log_function_call
    async def analyze_async(
        self,
        messages: list[Message],
        flags: GenerationFlags | None = None,
    ) -> ComplexityAnalysis:
        """Async analysis with mandatory LLM verification for fast path."""
        first_pass = self.analyze(messages, flags)

        if first_pass.is_complex:
            logger.info(
                "complexity_keywords_matched",
                reason=first_pass.reason,
                keywords=first_pass.keywords_matched,
            )
            return first_pass

        last_user_msg = self._get_last_user_message(messages)
        text = self._extract_text(last_user_msg.content) if last_user_msg else ""

        if self._should_skip_llm_check(text):
            logger.info("complexity_trivial_greeting", text_preview=text[:50])
            return first_pass

        needs_agent, reason = await self._llm_routing_check(text)
        logger.info(
            "complexity_llm_verification",
            needs_agent=needs_agent,
            reason=reason,
            model=self._routing_model,
            text_preview=text[:100],
        )

        if needs_agent or reason.startswith("llm_check_error") or reason == "no_api_key":
            if reason.startswith("llm_check_error") or reason == "no_api_key":
                logger.warning(
                    "complexity_defaulting_to_agent",
                    reason=reason,
                    text_preview=text[:100],
                )
                reason = f"conservative_default: {reason}"

            return ComplexityAnalysis(
                is_complex=True,
                reason=f"llm_verification: {reason}",
                keywords_matched=first_pass.keywords_matched,
                multimodal_detected=first_pass.multimodal_detected,
                has_images=first_pass.has_images,
                image_count=first_pass.image_count,
                text_preview=first_pass.text_preview,
            )

        logger.info(
            "complexity_confirmed_simple",
            reason=reason,
            text_preview=text[:100],
        )

        return first_pass

    def is_complex(
        self,
        messages: list[Message],
        flags: GenerationFlags | None = None,
    ) -> tuple[bool, str]:
        """
        Determine if the request is complex and needs sandbox execution.

        Returns:
            Tuple of (is_complex, reason)
        """
        analysis = self.analyze(messages, flags)
        return analysis.is_complex, analysis.reason


@lru_cache
def get_complexity_detector() -> ComplexityDetector:
    """Get cached complexity detector instance."""
    return ComplexityDetector(get_settings())
