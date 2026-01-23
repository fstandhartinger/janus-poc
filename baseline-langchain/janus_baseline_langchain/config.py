"""Configuration settings for the LangChain baseline competitor."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Baseline LangChain configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BASELINE_LANGCHAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8002, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # LLM settings
    model: str = Field(default="gpt-4o-mini", description="Default model")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible base URL",
    )
    temperature: float = Field(default=0.7, description="Model temperature")

    # Chutes settings
    chutes_api_key: Optional[str] = Field(
        default=None, description="Chutes API key for image and TTS"
    )

    # Web search
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")

    # HTTP behavior
    request_timeout: float = Field(default=30.0, description="HTTP request timeout")
    max_retries: int = Field(default=2, description="Max retries for external APIs")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
