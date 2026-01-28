"""Tests for complexity detection improvements."""

import pytest

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import Message, MessageRole
from janus_baseline_agent_cli.services import ComplexityDetector


@pytest.fixture
def detector() -> ComplexityDetector:
    """Create a complexity detector with default settings."""
    settings = Settings(complexity_threshold=100)
    return ComplexityDetector(settings)


class TestBrowserAutomation:
    """Test browser automation detection."""

    @pytest.mark.parametrize(
        "prompt",
        [
            "test https://janus.rodeo in a browser",
            "open https://example.com and take a screenshot",
            "visit the site and click the login button",
            "use playwright to test the form submission",
            "check if https://api.example.com/health returns 200",
            "automate filling out the registration form",
        ],
    )
    def test_browser_tasks_detected(
        self, detector: ComplexityDetector, prompt: str
    ) -> None:
        messages = [Message(role=MessageRole.USER, content=prompt)]
        analysis = detector.analyze(messages)
        assert analysis.is_complex, f"Should detect as complex: {prompt}"

    @pytest.mark.parametrize(
        "prompt",
        [
            "What is the capital of France?",
            "Explain how HTTP works",
            "Write a poem about the ocean",
            "Hello, how are you?",
        ],
    )
    def test_simple_tasks_not_complex(
        self, detector: ComplexityDetector, prompt: str
    ) -> None:
        messages = [Message(role=MessageRole.USER, content=prompt)]
        analysis = detector.analyze(messages)
        assert not analysis.is_complex, f"Should be simple: {prompt}"


class TestURLDetection:
    """Test URL interaction detection."""

    def test_url_with_test_keyword(self, detector: ComplexityDetector) -> None:
        messages = [Message(role=MessageRole.USER, content="test https://example.com")]
        analysis = detector.analyze(messages)
        assert analysis.is_complex
        assert "url_interaction" in analysis.reason

    def test_url_without_interaction(self, detector: ComplexityDetector) -> None:
        messages = [
            Message(role=MessageRole.USER, content="What is https://example.com?")
        ]
        analysis = detector.analyze(messages)
        assert analysis.is_complex is False


class TestConservativeDefaults:
    """Test conservative defaults on errors."""

    @pytest.mark.asyncio
    async def test_timeout_defaults_to_agent(
        self, detector: ComplexityDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_llm_check(text: str) -> tuple[bool, str]:
            return True, "llm_check_error: timeout"

        monkeypatch.setattr(detector, "_llm_routing_check", fake_llm_check)

        messages = [Message(role=MessageRole.USER, content="do something")]
        analysis = await detector.analyze_async(messages)
        assert analysis.is_complex
        assert "conservative_default" in analysis.reason

    @pytest.mark.asyncio
    async def test_no_api_key_defaults_to_agent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in (
            "OPENAI_API_KEY",
            "CHUTES_API_KEY",
            "BASELINE_OPENAI_API_KEY",
            "BASELINE_AGENT_CLI_OPENAI_API_KEY",
            "BASELINE_CHUTES_API_KEY",
            "BASELINE_AGENT_CLI_CHUTES_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        settings = Settings(openai_api_key=None)
        detector = ComplexityDetector(settings)

        messages = [Message(role=MessageRole.USER, content="do something")]
        analysis = await detector.analyze_async(messages)
        assert analysis.is_complex
        assert "no_api_key" in analysis.reason


class TestMultilingualKeywords:
    """Test multilingual keyword detection."""

    def test_german_separable_verbs(self, detector: ComplexityDetector) -> None:
        messages = [
            Message(
                role=MessageRole.USER,
                content="lade das repo von github herunter",
            )
        ]
        analysis = detector.analyze(messages)
        assert analysis.is_complex
        assert "herunterladen" in analysis.keywords_matched

    def test_git_repository_keywords(self, detector: ComplexityDetector) -> None:
        messages = [
            Message(
                role=MessageRole.USER,
                content="clone the chutes-api repo from github",
            )
        ]
        analysis = detector.analyze(messages)
        assert analysis.is_complex
        assert any(
            keyword in analysis.keywords_matched
            for keyword in ("git clone", "github", "repo", "clone the")
        )
