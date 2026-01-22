"""Benchmark runner configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Benchmark runner configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="JANUS_BENCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Target settings
    target_url: str = Field(
        default="http://localhost:8000",
        description="Target gateway URL",
    )
    model: str = Field(
        default="janus-baseline",
        description="Model name to use in requests",
    )

    # Timeout settings
    request_timeout: int = Field(default=300, description="Request timeout in seconds")
    ttft_timeout: int = Field(default=5, description="Time to first token timeout in seconds")

    # Scoring weights (must sum to 100)
    weight_quality: int = Field(default=45, description="Quality score weight percentage")
    weight_speed: int = Field(default=20, description="Speed score weight percentage")
    weight_cost: int = Field(default=15, description="Cost score weight percentage")
    weight_streaming: int = Field(default=10, description="Streaming continuity weight percentage")
    weight_multimodal: int = Field(default=10, description="Multimodal handling weight percentage")

    # Output settings
    output_dir: str = Field(default="./bench_results", description="Output directory for results")

    # Dataset settings
    seed: Optional[int] = Field(default=42, description="Random seed for reproducibility")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
