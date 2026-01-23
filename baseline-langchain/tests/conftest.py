"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from janus_baseline_langchain.config import get_settings
from janus_baseline_langchain.main import app


@pytest.fixture(autouse=True)
def reset_settings() -> None:
    """Reset cached settings between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the baseline competitor."""
    return TestClient(app)
