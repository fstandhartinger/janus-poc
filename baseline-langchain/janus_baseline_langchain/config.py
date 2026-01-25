"""Configuration settings for the LangChain baseline competitor."""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
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
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
        validation_alias=AliasChoices(
            "HOST",
            "BASELINE_LANGCHAIN_HOST",
        ),
    )
    port: int = Field(
        default=8080,
        description="Server port",
        validation_alias=AliasChoices(
            "PORT",
            "BASELINE_LANGCHAIN_PORT",
        ),
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        validation_alias=AliasChoices(
            "DEBUG",
            "BASELINE_LANGCHAIN_DEBUG",
        ),
    )

    # Model Router settings
    use_model_router: bool = Field(
        default=True,
        description="Enable composite model routing",
        validation_alias=AliasChoices(
            "USE_MODEL_ROUTER",
            "BASELINE_LANGCHAIN_USE_MODEL_ROUTER",
        ),
    )

    # LLM settings
    model: str = Field(default="zai-org/GLM-4.7-TEE", description="Default model")
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key",
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "BASELINE_LANGCHAIN_OPENAI_API_KEY",
        ),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible base URL",
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL",
            "BASELINE_LANGCHAIN_OPENAI_BASE_URL",
        ),
    )
    temperature: float = Field(default=0.7, description="Model temperature")

    # Vision settings
    vision_model_primary: str = Field(
        default="Qwen/Qwen3-VL-235B-A22B-Instruct",
        validation_alias=AliasChoices(
            "BASELINE_VISION_MODEL_PRIMARY",
            "BASELINE_LANGCHAIN_VISION_MODEL_PRIMARY",
        ),
        description="Primary vision model for image understanding",
    )
    vision_model_fallback: str = Field(
        default="chutesai/Mistral-Small-3.2-24B-Instruct-2506",
        validation_alias=AliasChoices(
            "BASELINE_VISION_MODEL_FALLBACK",
            "BASELINE_LANGCHAIN_VISION_MODEL_FALLBACK",
        ),
        description="Fallback vision model for image understanding",
    )
    vision_model_timeout: float = Field(
        default=60.0,
        validation_alias=AliasChoices(
            "BASELINE_VISION_MODEL_TIMEOUT",
            "BASELINE_LANGCHAIN_VISION_MODEL_TIMEOUT",
        ),
        description="Timeout in seconds for vision models",
    )
    enable_vision_routing: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "BASELINE_ENABLE_VISION_ROUTING",
            "BASELINE_LANGCHAIN_ENABLE_VISION_ROUTING",
        ),
        description="Enable routing to vision models when images are present",
    )

    # Chutes settings
    chutes_api_key: Optional[str] = Field(
        default=None,
        description="Chutes API key for image and TTS",
        validation_alias=AliasChoices(
            "CHUTES_API_KEY",
            "JANUS_CHUTES_API_KEY",
            "BASELINE_LANGCHAIN_CHUTES_API_KEY",
        ),
    )

    # Web search
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key",
        validation_alias=AliasChoices(
            "TAVILY_API_KEY",
            "BASELINE_LANGCHAIN_TAVILY_API_KEY",
        ),
    )

    # HTTP behavior
    request_timeout: float = Field(default=30.0, description="HTTP request timeout")
    max_retries: int = Field(default=2, description="Max retries for external APIs")

    # Memory service configuration
    memory_service_url: str = Field(
        default="https://janus-memory-service.onrender.com",
        description="URL of the memory service",
        validation_alias=AliasChoices(
            "MEMORY_SERVICE_URL",
            "BASELINE_LANGCHAIN_MEMORY_SERVICE_URL",
        ),
    )
    enable_memory_feature: bool = Field(
        default=True,
        description="Whether memory feature is enabled server-side",
        validation_alias=AliasChoices(
            "ENABLE_MEMORY_FEATURE",
            "BASELINE_LANGCHAIN_ENABLE_MEMORY_FEATURE",
        ),
    )
    memory_timeout_seconds: float = Field(
        default=5.0,
        description="Timeout for memory service calls",
        validation_alias=AliasChoices(
            "MEMORY_TIMEOUT_SECONDS",
            "BASELINE_LANGCHAIN_MEMORY_TIMEOUT_SECONDS",
        ),
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Log level",
        validation_alias=AliasChoices(
            "LOG_LEVEL",
            "BASELINE_LANGCHAIN_LOG_LEVEL",
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
