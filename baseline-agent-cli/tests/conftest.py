"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from janus_baseline_agent_cli.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the baseline competitor."""
    return TestClient(app)
