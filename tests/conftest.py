"""Pytest configuration and fixtures for baseline smoke tests."""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio

from tests.config import TestConfig, config
from tests.utils import is_service_available


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Shared test configuration."""
    return config


@pytest.fixture(scope="session")
def baseline_cli_url(test_config: TestConfig) -> str:
    """URL for baseline-agent-cli service."""
    return test_config.get_urls(test_config.default_mode())["baseline_cli"]


@pytest.fixture(scope="session")
def baseline_langchain_url(test_config: TestConfig) -> str:
    """URL for baseline-langchain service."""
    return test_config.get_urls(test_config.default_mode())["baseline_langchain"]


@pytest.fixture(scope="session")
def baseline_cli_model() -> str:
    """Default model for baseline-agent-cli smoke tests."""
    return os.getenv("TEST_BASELINE_CLI_MODEL", os.getenv("BASELINE_CLI_MODEL", "baseline"))


@pytest.fixture(scope="session")
def baseline_langchain_model() -> str:
    """Default model for baseline-langchain smoke tests."""
    return os.getenv(
        "TEST_BASELINE_LANGCHAIN_MODEL",
        os.getenv("BASELINE_LANGCHAIN_MODEL", "gpt-4o-mini"),
    )


@pytest.fixture(scope="session")
def gateway_url(test_config: TestConfig) -> str:
    """URL for gateway service."""
    return test_config.get_urls(test_config.default_mode())["gateway"]


@pytest.fixture(scope="session")
def ui_url(test_config: TestConfig) -> str:
    """URL for UI service."""
    return test_config.get_urls(test_config.default_mode())["ui"]


@pytest_asyncio.fixture
async def cli_client(
    baseline_cli_url: str, baseline_cli_model: str
) -> httpx.AsyncClient:
    """Client for baseline-agent-cli."""
    if not await is_service_available(baseline_cli_url):
        pytest.skip("baseline-agent-cli service not available")
    async with httpx.AsyncClient(
        base_url=baseline_cli_url,
        timeout=60.0,
        headers={"Content-Type": "application/json"},
    ) as client:
        client._janus_model = baseline_cli_model  # type: ignore[attr-defined]
        yield client


@pytest_asyncio.fixture
async def langchain_client(
    baseline_langchain_url: str, baseline_langchain_model: str
) -> httpx.AsyncClient:
    """Client for baseline-langchain."""
    if not await is_service_available(baseline_langchain_url):
        pytest.skip("baseline-langchain service not available")
    async with httpx.AsyncClient(
        base_url=baseline_langchain_url,
        timeout=60.0,
        headers={"Content-Type": "application/json"},
    ) as client:
        client._janus_model = baseline_langchain_model  # type: ignore[attr-defined]
        yield client


@pytest.fixture(params=["cli", "langchain"])
def client(request: pytest.FixtureRequest, cli_client, langchain_client):
    """Parameterized client for testing both baselines."""
    if request.param == "cli":
        return cli_client
    return langchain_client


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: smoke tests")
    config.addinivalue_line("markers", "smoke_baseline: baseline smoke tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow tests")
    config.addinivalue_line("markers", "visual: visual tests")
