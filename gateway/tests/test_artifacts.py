"""Tests for artifacts endpoint."""

import base64
import hashlib

from fastapi.testclient import TestClient

from janus_gateway.models import ArtifactType
from janus_gateway.services import get_artifact_store
from janus_gateway.services.artifact_store import build_data_url


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

    assert artifact.id
    assert artifact.type == ArtifactType.FILE
    assert artifact.mime_type == "text/plain"
    assert artifact.size_bytes == len(test_data)
    assert artifact.url.startswith("http://localhost:8000/v1/artifacts/")

    # Retrieve it
    response = client.get(f"/v1/artifacts/{artifact.id}")
    assert response.status_code == 200
    assert response.content == test_data
    assert response.headers["content-type"].startswith("text/plain")
    assert "test.txt" in response.headers["content-disposition"]
    assert response.headers["x-artifact-size"] == str(artifact.size_bytes)
    assert len(response.content) == artifact.size_bytes
    assert hashlib.sha256(response.content).hexdigest() == artifact.sha256

    # Cleanup
    store.delete(artifact.id)


def test_artifact_data_url_matches_sha() -> None:
    """Test base64 data URL decoding matches stored SHA256."""
    store = get_artifact_store()
    test_data = b"Small artifact payload"
    artifact = store.store(
        data=test_data,
        mime_type="text/plain",
        display_name="inline.txt",
        artifact_type=ArtifactType.FILE,
        gateway_base_url="http://localhost:8000",
    )

    try:
        data_url = build_data_url(test_data, artifact.mime_type)
        assert data_url is not None
        prefix, encoded = data_url.split(",", 1)
        assert prefix == "data:text/plain;base64"
        decoded = base64.b64decode(encoded)
        assert decoded == test_data
        assert hashlib.sha256(decoded).hexdigest() == artifact.sha256
    finally:
        store.delete(artifact.id)
