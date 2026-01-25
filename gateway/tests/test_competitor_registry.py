"""Tests for competitor registry configuration."""

from janus_gateway.config import get_settings
from janus_gateway.services.competitor_registry import get_competitor_registry


def _load_baseline_url() -> str:
    get_settings.cache_clear()
    get_competitor_registry.cache_clear()
    registry = get_competitor_registry()
    baseline = registry.get("baseline-cli-agent")
    assert baseline is not None
    return baseline.url


def _load_langchain_url() -> str:
    get_settings.cache_clear()
    get_competitor_registry.cache_clear()
    registry = get_competitor_registry()
    competitor = registry.get("baseline-langchain")
    assert competitor is not None
    return competitor.url


def test_baseline_url_hostport_uses_http(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_URL", "janus-baseline-agent-cli:10000")
    assert _load_baseline_url() == "http://janus-baseline-agent-cli:10000"


def test_baseline_url_hostname_uses_https(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_URL", "janus-baseline-agent-cli.onrender.com")
    assert _load_baseline_url() == "https://janus-baseline-agent-cli.onrender.com"


def test_langchain_url_hostport_uses_http(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_URL", "janus-baseline-langchain:10001")
    assert _load_langchain_url() == "http://janus-baseline-langchain:10001"


def test_langchain_url_hostname_uses_https(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_LANGCHAIN_URL", "janus-baseline-langchain.onrender.com")
    assert _load_langchain_url() == "https://janus-baseline-langchain.onrender.com"
