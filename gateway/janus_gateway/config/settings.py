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
    deep_research_timeout: int = Field(
        default=1200,
        description="Deep research request timeout in seconds",
    )

    # Gateway URL (for generating artifact URLs, etc.)
    gateway_url: Optional[str] = Field(
        default=None,
        description="Gateway public URL (for generating artifact URLs)",
        validation_alias=AliasChoices("GATEWAY_URL", "JANUS_GATEWAY_URL"),
    )
    default_competitor: str = Field(
        default="baseline-cli-agent",
        description="Default competitor ID to use when none specified",
        validation_alias=AliasChoices("DEFAULT_COMPETITOR", "JANUS_DEFAULT_COMPETITOR"),
    )

    # Competitor routing
    baseline_url: str = Field(
        default="https://janus-baseline-agent.onrender.com",
        description="Baseline agent CLI competitor base URL",
        validation_alias=AliasChoices(
            "COMPETITOR_URL",
            "BASELINE_AGENT_CLI_URL",
            "BASELINE_URL",
            "JANUS_BASELINE_URL",
        ),
    )
    baseline_langchain_url: str = Field(
        default="http://localhost:8082",
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

    # Chutes API
    chutes_api_key: Optional[str] = Field(
        default=None,
        description="Chutes API key",
        validation_alias=AliasChoices("CHUTES_API_KEY", "JANUS_CHUTES_API_KEY"),
    )
    pre_release_password: Optional[str] = Field(
        default=None,
        description="Pre-release password required for API access",
        validation_alias=AliasChoices("CHUTES_JANUS_PRE_RELEASE_PWD", "JANUS_PRE_RELEASE_PASSWORD"),
    )
    chutes_search_url: str = Field(
        default="https://chutes-search.onrender.com",
        description="Chutes search base URL",
        validation_alias=AliasChoices("CHUTES_SEARCH_URL", "JANUS_CHUTES_SEARCH_URL"),
    )
    firecrawl_api_key: Optional[str] = Field(
        default=None,
        description="Firecrawl API key",
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "JANUS_FIRECRAWL_API_KEY"),
    )
    firecrawl_base_url: str = Field(
        default="https://api.firecrawl.dev/v1",
        description="Firecrawl API base URL",
        validation_alias=AliasChoices("FIRECRAWL_BASE_URL", "JANUS_FIRECRAWL_BASE_URL"),
    )
    firecrawl_timeout: int = Field(
        default=30,
        description="Firecrawl request timeout in seconds",
    )
    whisper_endpoint: str = Field(
        default="https://chutes-whisper-large-v3.chutes.ai/transcribe",
        description="Whisper transcription endpoint URL",
        validation_alias=AliasChoices("WHISPER_ENDPOINT", "JANUS_WHISPER_ENDPOINT"),
    )

    # Memory service
    memory_service_url: str = Field(
        default="https://janus-memory-service.onrender.com",
        description="Memory service base URL",
        validation_alias=AliasChoices("MEMORY_SERVICE_URL", "JANUS_MEMORY_SERVICE_URL"),
    )

    # Scoring service
    scoring_service_url: str = Field(
        default="https://janus-scoring-service.onrender.com",
        description="Scoring service base URL",
        validation_alias=AliasChoices("SCORING_SERVICE_URL", "JANUS_SCORING_SERVICE_URL"),
    )

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
