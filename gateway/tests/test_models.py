"""Tests for models endpoint."""

from fastapi.testclient import TestClient


def test_list_models(client: TestClient) -> None:
    """Test listing available models."""
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    # Should have at least the baseline model
    assert len(data["data"]) >= 1
    model = data["data"][0]
    assert "id" in model
    assert model["object"] == "model"
