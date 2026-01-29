"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from janus_baseline_agent_cli import __version__


def test_health_check(client: TestClient) -> None:
    """Test health check returns OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert isinstance(data["sandbox_available"], bool)
    assert data["features"]["agent_sandbox"] == data["sandbox_available"]
    assert "memory" in data["features"]
    assert "vision" in data["features"]
    assert "warm_pool" in data
    assert isinstance(data["warm_pool"]["enabled"], bool)
    assert isinstance(data["warm_pool"]["size"], int)
    assert isinstance(data["warm_pool"]["target"], int)
