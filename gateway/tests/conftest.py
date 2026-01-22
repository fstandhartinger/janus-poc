"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from janus_gateway.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the gateway."""
    return TestClient(app)
