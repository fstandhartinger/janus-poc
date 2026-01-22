"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from janus_baseline.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the baseline competitor."""
    return TestClient(app)
