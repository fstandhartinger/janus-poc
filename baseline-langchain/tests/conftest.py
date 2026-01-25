"""Pytest configuration and fixtures."""

import importlib.util

import pytest
from fastapi.testclient import TestClient

if importlib.util.find_spec("langchain_core") is None:
    pytest.skip("langchain_core not installed", allow_module_level=True)

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


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "smoke: smoke tests")
