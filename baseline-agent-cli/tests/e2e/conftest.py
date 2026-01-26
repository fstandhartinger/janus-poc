"""Shared configuration for baseline agent CLI E2E tests."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import pytest

from janus_baseline_agent_cli.config import Settings


@dataclass(frozen=True)
class E2ESettings:
    """Resolved settings for E2E tests."""

    gateway_url: str
    baseline_cli_url: str
    enabled: bool
    chutes_access_token: str | None


def _load_e2e_settings() -> E2ESettings:
    settings = Settings()
    return E2ESettings(
        gateway_url=settings.e2e_gateway_url.rstrip("/"),
        baseline_cli_url=settings.e2e_baseline_cli_url.rstrip("/"),
        enabled=settings.e2e_enabled,
        chutes_access_token=(
            os.getenv("BASELINE_AGENT_CLI_E2E_CHUTES_API_KEY")
            or os.getenv("CHUTES_API_KEY")
        ),
    )


E2E_SETTINGS = _load_e2e_settings()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "e2e: end-to-end tests hitting deployed services")
    config.addinivalue_line("markers", "timeout(seconds): per-test timeout for E2E runs")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if E2E_SETTINGS.enabled:
        return
    skip_marker = pytest.mark.skip(
        reason="E2E tests require BASELINE_AGENT_CLI_E2E_ENABLED=true",
    )
    e2e_root = Path(__file__).parent.resolve()
    for item in items:
        item_path = Path(str(item.fspath)).resolve()
        if item_path == e2e_root or e2e_root in item_path.parents:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def e2e_settings() -> E2ESettings:
    return E2E_SETTINGS


@pytest.fixture(scope="session")
def chutes_access_token(e2e_settings: E2ESettings) -> str | None:
    return e2e_settings.chutes_access_token
