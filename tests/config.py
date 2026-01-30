"""Shared configuration for Janus test suites."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestConfig(BaseSettings):
    """Test configuration with local/deployed targets."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    gateway_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("TEST_GATEWAY_URL", "GATEWAY_URL"),
    )
    baseline_cli_url: str = Field(
        default="http://localhost:8081",
        validation_alias=AliasChoices("TEST_BASELINE_CLI_URL", "BASELINE_CLI_URL"),
    )
    baseline_langchain_url: str = Field(
        default="http://localhost:8082",
        validation_alias=AliasChoices("TEST_BASELINE_LANGCHAIN_URL", "BASELINE_LANGCHAIN_URL"),
    )
    ui_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("TEST_UI_URL", "UI_URL"),
    )

    gateway_deployed_url: str = Field(
        default="https://janus-gateway-bqou.onrender.com",
        validation_alias=AliasChoices("TEST_GATEWAY_DEPLOYED_URL"),
    )
    baseline_cli_deployed_url: str = Field(
        default="https://janus-baseline-agent.onrender.com",
        validation_alias=AliasChoices("TEST_BASELINE_CLI_DEPLOYED_URL"),
    )
    baseline_langchain_deployed_url: str = Field(
        default="https://janus-baseline-langchain.onrender.com",
        validation_alias=AliasChoices("TEST_BASELINE_LANGCHAIN_DEPLOYED_URL"),
    )
    ui_deployed_url: str = Field(
        default="https://janus.rodeo",
        validation_alias=AliasChoices("TEST_UI_DEPLOYED_URL"),
    )
    memory_service_deployed_url: str = Field(
        default="https://janus-memory-service.onrender.com",
        validation_alias=AliasChoices("TEST_MEMORY_SERVICE_DEPLOYED_URL"),
    )

    test_mode: Literal["local", "deployed", "both"] = Field(
        default="local", validation_alias=AliasChoices("TEST_MODE")
    )
    chutes_fingerprint: str = Field(
        default="",
        validation_alias=AliasChoices("CHUTES_FINGERPRINT", "TEST_CHUTES_FINGERPRINT"),
    )
    chutes_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("CHUTES_API_KEY", "TEST_CHUTES_API_KEY"),
    )

    health_timeout: int = Field(
        default=10, validation_alias=AliasChoices("TEST_HEALTH_TIMEOUT")
    )
    simple_request_timeout: int = Field(
        default=60, validation_alias=AliasChoices("TEST_SIMPLE_REQUEST_TIMEOUT", "TEST_REQUEST_TIMEOUT")
    )
    complex_request_timeout: int = Field(
        default=300, validation_alias=AliasChoices("TEST_COMPLEX_REQUEST_TIMEOUT")
    )
    streaming_timeout: int = Field(
        default=300, validation_alias=AliasChoices("TEST_STREAMING_TIMEOUT")
    )
    ui_timeout: int = Field(default=30000, validation_alias=AliasChoices("TEST_UI_TIMEOUT"))

    screenshot_dir: str = Field(
        default="./test-screenshots",
        validation_alias=AliasChoices("TEST_SCREENSHOT_DIR"),
    )
    viewports: list[dict[str, int | str]] = [
        {"name": "desktop", "width": 1920, "height": 1080},
        {"name": "tablet", "width": 768, "height": 1024},
        {"name": "mobile", "width": 375, "height": 812},
    ]

    def _normalize_mode(self, mode: str | None) -> str:
        value = (mode or self.test_mode).lower()
        if value not in {"local", "deployed", "both"}:
            return "local"
        return value

    def default_mode(self) -> str:
        mode = self._normalize_mode(None)
        return "local" if mode == "both" else mode

    def modes(self) -> list[str]:
        mode = self._normalize_mode(None)
        if mode == "both":
            return ["local", "deployed"]
        return [mode]

    def get_urls(self, mode: str | None = None) -> dict[str, str]:
        selected = self._normalize_mode(mode)
        if selected == "both":
            selected = "local"
        if selected == "deployed":
            return {
                "gateway": self.gateway_deployed_url,
                "baseline_cli": self.baseline_cli_deployed_url,
                "baseline_langchain": self.baseline_langchain_deployed_url,
                "ui": self.ui_deployed_url,
                "memory_service": self.memory_service_deployed_url,
            }
        return {
            "gateway": self.gateway_url,
            "baseline_cli": self.baseline_cli_url,
            "baseline_langchain": self.baseline_langchain_url,
            "ui": self.ui_url,
            "memory_service": "http://localhost:8003",  # Local memory service
        }

    def get_url(self, service: str, mode: str | None = None) -> str:
        """Get URL for a specific service based on test mode."""
        urls = self.get_urls(mode)
        return urls.get(service, urls.get("gateway"))

    @property
    def request_timeout(self) -> int:
        """Backward-compatible alias for simple_request_timeout."""
        return self.simple_request_timeout


config = TestConfig()
