"""Configuration settings for the baseline competitor."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Baseline competitor configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BASELINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8001, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # LLM settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: Optional[str] = Field(
        default=None, description="Custom OpenAI-compatible base URL"
    )
    model: str = Field(default="gpt-4o-mini", description="Default model for fast path")
    max_tokens: int = Field(default=4096, description="Max tokens for responses")
    temperature: float = Field(default=0.7, description="Default temperature")

    # Sandy settings (for complex path)
    sandy_base_url: Optional[str] = Field(
        default=None,
        validation_alias="SANDY_BASE_URL",
        description="Sandy API base URL",
    )
    sandy_api_key: Optional[str] = Field(
        default=None,
        validation_alias="SANDY_API_KEY",
        description="Sandy API key",
    )
    sandy_timeout: int = Field(default=300, description="Sandy sandbox timeout in seconds")

    # Agent pack configuration
    agent_pack_path: str = Field(
        default="./agent-pack", description="Path to the baseline agent pack directory"
    )
    system_prompt_path: str = Field(
        default="./agent-pack/prompts/system.md",
        description="Path to the system prompt used by the CLI agent",
    )
    enable_web_search: bool = Field(default=True, description="Enable web search tools")
    enable_code_execution: bool = Field(
        default=True, description="Enable code execution tools"
    )
    enable_file_tools: bool = Field(default=True, description="Enable file tooling")

    # Complexity detection
    complexity_threshold: int = Field(
        default=100, description="Token count threshold for complex path"
    )
    always_use_agent: bool = Field(
        default=False,
        description="Always route to agent sandbox, bypass complexity detection",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
