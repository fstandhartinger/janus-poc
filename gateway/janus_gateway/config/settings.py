"""Gateway settings with environment variable configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="JANUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Gateway settings
    request_timeout: int = Field(default=300, description="Request timeout in seconds")
    max_request_size: int = Field(default=10_485_760, description="Max request size in bytes (10MB)")
    keep_alive_interval: float = Field(default=1.5, description="SSE keep-alive interval in seconds")

    # Competitor routing
    baseline_url: str = Field(
        default="https://janus-baseline-agent.onrender.com",
        description="Baseline agent CLI competitor base URL",
        validation_alias=AliasChoices(
            "BASELINE_AGENT_CLI_URL",
            "BASELINE_URL",
            "JANUS_BASELINE_URL",
        ),
    )
    baseline_langchain_url: str = Field(
        default="http://localhost:8002",
        description="Baseline LangChain competitor base URL",
        validation_alias=AliasChoices(
            "BASELINE_LANGCHAIN_URL",
            "JANUS_BASELINE_LANGCHAIN_URL",
        ),
    )

    # Sandy settings
    sandy_base_url: Optional[str] = Field(default=None, description="Sandy API base URL")
    sandy_api_key: Optional[str] = Field(default=None, description="Sandy API key")
    sandy_preferred_upstream: Optional[str] = Field(default=None, description="Sandy preferred upstream")

    # Artifact storage
    artifact_storage_path: str = Field(default="/tmp/janus_artifacts", description="Local artifact storage path")
    artifact_ttl_seconds: int = Field(default=3600, description="Artifact TTL in seconds")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json or console)")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
