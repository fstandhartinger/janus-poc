"""Configuration settings for the baseline competitor."""

from functools import lru_cache
from typing import Any, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource


class Settings(BaseSettings):
    """Baseline competitor configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="BASELINE_AGENT_CLI_",
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        legacy_env = EnvSettingsSource(settings_cls, env_prefix="BASELINE_")
        legacy_dotenv = DotEnvSettingsSource(
            settings_cls,
            env_file=settings_cls.model_config.get("env_file"),
            env_file_encoding=settings_cls.model_config.get("env_file_encoding"),
            env_prefix="BASELINE_",
        )
        return (
            init_settings,
            env_settings,
            legacy_env,
            dotenv_settings,
            legacy_dotenv,
            file_secret_settings,
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

    # Chutes API
    chutes_api_key: Optional[str] = Field(
        default=None,
        description="Chutes API key",
        validation_alias=AliasChoices("CHUTES_API_KEY", "JANUS_CHUTES_API_KEY"),
    )

    # Vision settings
    vision_model_primary: str = Field(
        default="Qwen/Qwen3-VL-235B-A22B-Instruct",
        description="Primary vision model for image understanding",
    )
    vision_model_fallback: str = Field(
        default="chutesai/Mistral-Small-3.2-24B-Instruct-2506",
        description="Fallback vision model for image understanding",
    )
    vision_model_timeout: float = Field(
        default=60.0, description="Timeout in seconds for vision models"
    )
    enable_vision_routing: bool = Field(
        default=True, description="Enable routing to vision models when images are present"
    )

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
    artifact_port: int = Field(
        default=8787,
        validation_alias="JANUS_ARTIFACT_PORT",
        description="Sandbox artifact server port",
    )
    artifact_dir: str = Field(
        default="/workspace/artifacts",
        validation_alias="JANUS_ARTIFACTS_DIR",
        description="Sandbox artifacts directory",
    )
    artifact_ttl_seconds: int = Field(
        default=3600, description="Artifact TTL in seconds"
    )

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
    baseline_agent: str = Field(
        default="aider",
        validation_alias="JANUS_BASELINE_AGENT",
        description="CLI agent command to run inside the sandbox",
    )

    # Complexity detection
    complexity_threshold: int = Field(
        default=100, description="Token count threshold for complex path"
    )
    always_use_agent: bool = Field(
        default=False,
        description="Always route to agent sandbox, bypass complexity detection",
    )
    llm_routing_model: str = Field(
        default="zai-org/GLM-4.7-Flash",
        description="Fast model to use for routing decisions",
    )
    llm_routing_timeout: float = Field(
        default=3.0,
        description="Timeout in seconds for LLM routing check",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
