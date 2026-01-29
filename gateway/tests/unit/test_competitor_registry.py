"""Unit tests for competitor registry."""

from janus_gateway.models import CompetitorInfo
from janus_gateway.services.competitor_registry import CompetitorRegistry


def test_register_competitor() -> None:
    registry = CompetitorRegistry()
    competitor = CompetitorInfo(
        id="test-competitor",
        name="Test",
        description="Test competitor",
        url="http://localhost:9999",
        enabled=True,
    )
    registry.register(competitor)
    ids = {entry.id for entry in registry.list_all(enabled_only=False)}
    assert "test-competitor" in ids


def test_get_competitor_by_id() -> None:
    registry = CompetitorRegistry()
    competitor = CompetitorInfo(
        id="test-competitor",
        name="Test",
        url="http://localhost:9999",
        enabled=True,
    )
    registry.register(competitor)
    result = registry.get("test-competitor")
    assert result is not None
    assert result.url == "http://localhost:9999"


def test_get_default_competitor() -> None:
    registry = CompetitorRegistry()
    competitor = CompetitorInfo(
        id="custom-default",
        name="Default",
        url="http://localhost:9000",
        enabled=True,
    )
    registry.register(competitor, is_default=True)
    result = registry.get_default()
    assert result is not None
    assert result.id == "custom-default"


def test_unknown_competitor_returns_none() -> None:
    registry = CompetitorRegistry()
    assert registry.get("nonexistent") is None


def test_list_enabled_only() -> None:
    registry = CompetitorRegistry()
    registry.register(
        CompetitorInfo(
            id="active",
            name="A",
            url="http://a",
            enabled=True,
        )
    )
    registry.register(
        CompetitorInfo(
            id="inactive",
            name="B",
            url="http://b",
            enabled=False,
        )
    )
    active_ids = {entry.id for entry in registry.list_all(enabled_only=True)}
    assert "active" in active_ids
    assert "inactive" not in active_ids
