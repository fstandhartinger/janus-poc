"""Pytest configuration and fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("BASELINE_URL", "http://localhost:8081")
os.environ.setdefault("CHUTES_JANUS_PRE_RELEASE_PWD", "")

from janus_gateway.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the gateway."""
    return TestClient(app)
