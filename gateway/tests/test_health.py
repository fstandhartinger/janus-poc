"""Tests for health endpoint."""

from fastapi.testclient import TestClient

from janus_gateway import __version__


def test_health_check(client: TestClient) -> None:
    """Test health check returns OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
    assert "timestamp" in data
