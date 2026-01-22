"""Tests for artifacts endpoint."""

import pytest
from fastapi.testclient import TestClient

from janus_gateway.models import ArtifactType
from janus_gateway.services import get_artifact_store


def test_artifact_not_found(client: TestClient) -> None:
    """Test that missing artifacts return 404."""
    response = client.get("/v1/artifacts/nonexistent")
    assert response.status_code == 404


def test_artifact_retrieval(client: TestClient) -> None:
    """Test storing and retrieving an artifact."""
    store = get_artifact_store()

    # Store a test artifact
    test_data = b"Hello, World!"
    artifact = store.store(
        data=test_data,
        mime_type="text/plain",
        display_name="test.txt",
        artifact_type=ArtifactType.FILE,
        gateway_base_url="http://localhost:8000",
    )

    # Retrieve it
    response = client.get(f"/v1/artifacts/{artifact.id}")
    assert response.status_code == 200
    assert response.content == test_data
    assert response.headers["content-type"].startswith("text/plain")
    assert "test.txt" in response.headers["content-disposition"]

    # Cleanup
    store.delete(artifact.id)
