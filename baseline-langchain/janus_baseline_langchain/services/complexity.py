"""Complexity detection service to route between fast and agent paths."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Optional

import httpx
import structlog

from janus_baseline_langchain.config import Settings, get_settings
from janus_baseline_langchain.models import GenerationFlags, Message, MessageContent
from janus_baseline_langchain.services.vision import contains_images, count_images
from janus_baseline_langchain.services.robust import robust_parse_tool_call

logger = structlog.get_logger()

ROUTING_ENDPOINT = "https://llm.chutes.ai/v1/chat/completions"

ROUTING_MODELS = [
    "XiaomiMiMo/MiMo-V2-Flash",
    "deepseek-ai/DeepSeek-V3",
    "zai-org/GLM-4.7-TEE",
]

ROUTING_PROMPT = """Analyze this user request and decide if it needs agent capabilities.

Agent capabilities are REQUIRED for:
- Image/video/audio generation ("generate an image", "create a video", "text to speech")
- Code execution ("run this code", "execute", "test this script")
- Web search ("search for", "find current", "latest news")
- File operations ("download", "save to file", "read file")
- Browser automation ("test in browser", "open URL", "take screenshot")
- GUI/Desktop interaction ("click button", "type into", "automate")
- API calls ("call the API", "make a request", "curl")
- Testing ("run tests", "verify", "check if working")
- Any task requiring interaction with external systems, URLs, or tools

Direct LLM response is sufficient for:
- General conversation and chitchat
- Explanations, definitions, and summaries that don't require up-to-date information
- Simple math (without needing to run code)
- Writing assistance (text generation without execution)
- Questions answered from general knowledge without external tools

IMPORTANT: When in doubt, choose needs_agent=true.

User request: {user_message}

Call the use_agent function with your decision."""

USE_AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "use_agent",
        "description": "Decide whether this request needs the agent tools.",
        "parameters": {
            "type": "object",
            "properties": {
                "needs_agent": {
                    "type": "boolean",
                    "description": "True if request needs agent tools.",
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

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)


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
    """Detects whether a request should use the fast path or agent path."""

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
        "herunterladen",
        "lade herunter",
        "downloaden",
        "suche",
        "such nach",
        "recherchiere",
        "finde heraus",
        "fuhre aus",
        "ausfuhren",
        "starte",
        "kompiliere",
        "teste",
        "debugge",
        "speichere",
        "schreibe",
        "erstelle datei",
        "losche",
        "offne",
        "besuche",
        "navigiere",
        "generiere",
        "erstelle bild",
        "erzeuge",
        "zusammenfassung",
        "analysiere",
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

    GERMAN_SEPARABLE_VERBS = [
        (r"lade\s+.+\s+herunter", "herunterladen"),
        (r"such\s+.+\s+nach", "suchen nach"),
        (r"fuhr\s+.+\s+aus", "ausfuhren"),
        (r"gib\s+.+\s+zusammenfassung", "zusammenfassung"),
        (r"fass\s+.+\s+zusammen", "zusammenfassung"),
    ]

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._threshold = settings.complexity_threshold
        self._routing_model = settings.llm_routing_model
        self._routing_timeout = settings.llm_routing_timeout

    def _get_last_user_message(self, messages: list[Message]) -> Optional[Message]:
        for msg in reversed(messages):
            if msg.role.value == "user":
                return msg
        return None

    def _normalize_text(self, text: str) -> str:
        cleaned = "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()
        return " ".join(cleaned.split())

    def _should_skip_llm_check(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        return not normalized or normalized in TRIVIAL_GREETINGS

    def _extract_text(self, content: Optional[MessageContent]) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        text_parts: list[str] = []
        for part in content:
            if hasattr(part, "text"):
                text_parts.append(part.text)
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return " ".join(text_parts)

    def _estimate_tokens(self, text: str) -> int:
        words = len(text.split())
        return int(words * 1.3)

    def _matched_complex_keywords(self, text: str) -> list[str]:
        text_lower = text.lower()
        matches = [keyword for keyword in self.COMPLEX_KEYWORDS if keyword in text_lower]
        for pattern, keyword in self.GERMAN_SEPARABLE_VERBS:
            if re.search(pattern, text_lower):
                matches.append(keyword)
        return matches

    def _has_complex_keywords(self, text: str) -> bool:
        return bool(self._matched_complex_keywords(text))

    def _has_code_blocks(self, text: str) -> bool:
        return "```" in text

    def _is_multimodal_request(self, text: str) -> bool:
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
        return bool(URL_PATTERN.search(text))

    def _url_suggests_interaction(self, text: str) -> bool:
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
        if self._settings.always_use_agent:
            return ComplexityAnalysis(
                is_complex=True,
                reason="always_use_agent",
                keywords_matched=[],
                multimodal_detected=False,
                has_images=contains_images(messages),
                image_count=count_images(messages),
                text_preview="",
            )

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

        total_tokens = sum(
            self._estimate_tokens(self._extract_text(m.content)) for m in messages
        )
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
        self, client: httpx.AsyncClient, model: str, text: str, token: str
    ) -> tuple[bool, str, bool]:
        try:
            response = await client.post(
                ROUTING_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": ROUTING_PROMPT.replace("{user_message}", text[:500]),
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

    async def _llm_routing_check(self, text: str) -> tuple[bool, str]:
        token = self._settings.openai_api_key or self._settings.chutes_api_key
        if not token:
            return False, "no_api_key"

        models_to_try = [self._routing_model] + [
            model for model in ROUTING_MODELS if model != self._routing_model
        ]

        async with httpx.AsyncClient(timeout=self._routing_timeout) as client:
            for model in models_to_try:
                needs_agent, reason, success = await self._try_routing_model(
                    client, model, text, token
                )
                if success:
                    logger.info(
                        "llm_routing_success",
                        model=model,
                        needs_agent=needs_agent,
                        reason=reason,
                    )
                    return needs_agent, reason

        return True, "llm_check_error: all models unavailable"

    async def analyze_async(
        self,
        messages: list[Message],
        flags: GenerationFlags | None = None,
    ) -> ComplexityAnalysis:
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
        if reason == "no_api_key":
            logger.info("complexity_llm_skipped_no_api_key", text_preview=text[:100])
            return first_pass

        logger.info(
            "complexity_llm_verification",
            needs_agent=needs_agent,
            reason=reason,
            model=self._routing_model,
            text_preview=text[:100],
        )

        if needs_agent or reason.startswith("llm_check_error"):
            if reason.startswith("llm_check_error"):
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

        logger.info("complexity_confirmed_simple", reason=reason, text_preview=text[:100])
        return first_pass

    def is_complex(
        self,
        messages: list[Message],
        flags: GenerationFlags | None = None,
    ) -> tuple[bool, str]:
        analysis = self.analyze(messages, flags)
        return analysis.is_complex, analysis.reason


@lru_cache
def get_complexity_detector() -> ComplexityDetector:
    """Get cached complexity detector instance."""
    return ComplexityDetector(get_settings())
