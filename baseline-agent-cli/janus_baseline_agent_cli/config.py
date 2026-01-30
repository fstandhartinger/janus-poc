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
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
        validation_alias=AliasChoices(
            "HOST",
            "BASELINE_AGENT_CLI_HOST",
            "BASELINE_HOST",
        ),
    )
    port: int = Field(
        default=8080,
        description="Server port",
        validation_alias=AliasChoices(
            "PORT",
            "BASELINE_AGENT_CLI_PORT",
            "BASELINE_PORT",
        ),
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        validation_alias=AliasChoices(
            "DEBUG",
            "BASELINE_AGENT_CLI_DEBUG",
            "BASELINE_DEBUG",
        ),
    )

    # LLM settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key",
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "BASELINE_AGENT_CLI_OPENAI_API_KEY",
            "BASELINE_OPENAI_API_KEY",
        ),
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom OpenAI-compatible base URL",
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL",
            "BASELINE_AGENT_CLI_OPENAI_BASE_URL",
            "BASELINE_OPENAI_BASE_URL",
        ),
    )
    model: str = Field(default="janus-router", description="Default model for fast path")
    direct_model: str = Field(
        default="tngtech/TNG-R1T-Chimera-Turbo",
        description="Direct model when router is disabled",
        validation_alias=AliasChoices(
            "DIRECT_MODEL",
            "BASELINE_AGENT_CLI_DIRECT_MODEL",
            "BASELINE_DIRECT_MODEL",
        ),
    )
    max_tokens: int = Field(default=4096, description="Max tokens for responses")
    temperature: float = Field(default=0.7, description="Default temperature")

    # Chutes API
    chutes_api_key: Optional[str] = Field(
        default=None,
        description="Chutes API key",
        validation_alias=AliasChoices(
            "CHUTES_API_KEY",
            "JANUS_CHUTES_API_KEY",
            "BASELINE_AGENT_CLI_CHUTES_API_KEY",
            "BASELINE_CHUTES_API_KEY",
        ),
    )
    chutes_api_base: str = Field(
        default="https://llm.chutes.ai/v1",
        description="Chutes API base URL",
        validation_alias=AliasChoices(
            "CHUTES_API_BASE",
            "BASELINE_AGENT_CLI_CHUTES_API_BASE",
            "BASELINE_CHUTES_API_BASE",
        ),
    )
    chutes_search_url: str = Field(
        default="https://chutes-search.onrender.com",
        description="Chutes search base URL",
        validation_alias=AliasChoices(
            "CHUTES_SEARCH_URL",
            "JANUS_CHUTES_SEARCH_URL",
            "BASELINE_AGENT_CLI_CHUTES_SEARCH_URL",
            "BASELINE_CHUTES_SEARCH_URL",
        ),
    )
    serper_api_key: Optional[str] = Field(
        default=None,
        description="Serper API key for web search",
        validation_alias=AliasChoices(
            "SERPER_API_KEY",
            "BASELINE_AGENT_CLI_SERPER_API_KEY",
            "BASELINE_SERPER_API_KEY",
        ),
    )
    searxng_api_url: Optional[str] = Field(
        default=None,
        description="SearXNG API URL for web search fallback",
        validation_alias=AliasChoices(
            "SEARXNG_API_URL",
            "BASELINE_AGENT_CLI_SEARXNG_API_URL",
            "BASELINE_SEARXNG_API_URL",
        ),
    )

    # Model router configuration
    use_model_router: bool = Field(
        default=True,
        description="Enable local model router",
        validation_alias=AliasChoices(
            "USE_MODEL_ROUTER",
            "BASELINE_AGENT_CLI_USE_MODEL_ROUTER",
            "BASELINE_USE_MODEL_ROUTER",
        ),
    )
    router_host: str = Field(
        default="127.0.0.1",
        description="Model router host",
        validation_alias=AliasChoices(
            "ROUTER_HOST",
            "BASELINE_AGENT_CLI_ROUTER_HOST",
            "BASELINE_ROUTER_HOST",
        ),
    )
    router_port: int = Field(
        default=8000,
        description="Model router port",
        validation_alias=AliasChoices(
            "ROUTER_PORT",
            "BASELINE_AGENT_CLI_ROUTER_PORT",
            "BASELINE_ROUTER_PORT",
        ),
    )
    public_router_url: Optional[str] = Field(
        default=None,
        description="Public URL for the model router (for Sandy agent access). "
        "If set, Sandy agents will route LLM calls through this URL for smart model selection.",
        validation_alias=AliasChoices(
            "PUBLIC_ROUTER_URL",
            "BASELINE_AGENT_CLI_PUBLIC_ROUTER_URL",
            "BASELINE_PUBLIC_ROUTER_URL",
        ),
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
    sandy_agent_timeout: int = Field(
        default=600,
        description="Sandy sandbox timeout in seconds",
        validation_alias=AliasChoices(
            "SANDY_AGENT_TIMEOUT",
            "BASELINE_AGENT_CLI_SANDY_AGENT_TIMEOUT",
            "BASELINE_SANDY_AGENT_TIMEOUT",
            "SANDY_TIMEOUT",
            "BASELINE_AGENT_CLI_SANDY_TIMEOUT",
            "BASELINE_SANDY_TIMEOUT",
        ),
    )
    sandy_git_timeout: int = Field(
        default=120,
        description="Git operation timeout in seconds inside Sandy sandboxes",
        validation_alias=AliasChoices(
            "SANDY_GIT_TIMEOUT",
            "BASELINE_AGENT_CLI_SANDY_GIT_TIMEOUT",
            "BASELINE_SANDY_GIT_TIMEOUT",
            "JANUS_GIT_TIMEOUT",
            "BASELINE_AGENT_CLI_GIT_TIMEOUT",
            "BASELINE_GIT_TIMEOUT",
        ),
    )
    http_client_timeout: int = Field(
        default=660,
        description="HTTP client timeout in seconds",
        validation_alias=AliasChoices(
            "HTTP_CLIENT_TIMEOUT",
            "BASELINE_AGENT_CLI_HTTP_CLIENT_TIMEOUT",
            "BASELINE_HTTP_CLIENT_TIMEOUT",
        ),
    )
    sse_keepalive_interval: int = Field(
        default=15,
        description="SSE keepalive interval in seconds",
        validation_alias=AliasChoices(
            "SSE_KEEPALIVE_INTERVAL",
            "BASELINE_AGENT_CLI_SSE_KEEPALIVE_INTERVAL",
            "BASELINE_SSE_KEEPALIVE_INTERVAL",
        ),
    )
    artifact_port: int = Field(
        default=5173,
        validation_alias="JANUS_ARTIFACT_PORT",
        description="Sandbox artifact server port (should match Sandy runtime port)",
    )
    artifact_dir: str = Field(
        default="/workspace/artifacts",
        validation_alias="JANUS_ARTIFACTS_DIR",
        description="Sandbox artifacts directory",
    )
    artifact_ttl_seconds: int = Field(
        default=3600, description="Artifact TTL in seconds"
    )
    artifact_grace_seconds: int = Field(
        default=30,
        description="Seconds to keep sandbox alive after emitting artifacts",
        validation_alias=AliasChoices(
            "JANUS_ARTIFACT_GRACE_SECONDS",
            "BASELINE_AGENT_CLI_ARTIFACT_GRACE_SECONDS",
            "BASELINE_ARTIFACT_GRACE_SECONDS",
        ),
    )

    # Memory service configuration
    memory_service_url: str = Field(
        default="https://janus-memory-service.onrender.com",
        description="URL of the memory service",
        validation_alias=AliasChoices(
            "MEMORY_SERVICE_URL",
            "BASELINE_AGENT_CLI_MEMORY_SERVICE_URL",
            "BASELINE_MEMORY_SERVICE_URL",
        ),
    )

    # Browser session service configuration
    browser_session_service_url: str = Field(
        default="https://janus-browser-session-service.onrender.com",
        description="URL of the browser session storage service",
        validation_alias=AliasChoices(
            "BROWSER_SESSION_SERVICE_URL",
            "BASELINE_AGENT_CLI_BROWSER_SESSION_SERVICE_URL",
            "BASELINE_BROWSER_SESSION_SERVICE_URL",
        ),
    )
    enable_memory_feature: bool = Field(
        default=True,
        description="Whether memory feature is enabled server-side",
        validation_alias=AliasChoices(
            "ENABLE_MEMORY_FEATURE",
            "BASELINE_AGENT_CLI_ENABLE_MEMORY_FEATURE",
            "BASELINE_ENABLE_MEMORY_FEATURE",
        ),
    )
    memory_timeout_seconds: float = Field(
        default=5.0,
        description="Timeout for memory service calls",
        validation_alias=AliasChoices(
            "MEMORY_TIMEOUT_SECONDS",
            "BASELINE_AGENT_CLI_MEMORY_TIMEOUT_SECONDS",
            "BASELINE_MEMORY_TIMEOUT_SECONDS",
        ),
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
        default="claude-code",
        validation_alias="JANUS_BASELINE_AGENT",
        description="CLI agent command to run inside the sandbox",
    )
    use_sandy_agent_api: bool = Field(
        default=True,
        validation_alias="USE_SANDY_AGENT_API",
        description="Use Sandy's built-in agent/run API instead of manual exec (faster, better configured)",
    )

    # Warm pool settings
    warm_pool_enabled: bool = Field(
        default=True,
        description="Enable warm pool for Sandy sandboxes",
        validation_alias=AliasChoices(
            "WARM_POOL_ENABLED",
            "BASELINE_AGENT_CLI_WARM_POOL_ENABLED",
            "BASELINE_WARM_POOL_ENABLED",
        ),
    )
    warm_pool_size: int = Field(
        default=2,
        description="Number of warm sandboxes to maintain",
        validation_alias=AliasChoices(
            "WARM_POOL_SIZE",
            "BASELINE_AGENT_CLI_WARM_POOL_SIZE",
            "BASELINE_WARM_POOL_SIZE",
        ),
    )
    warm_pool_max_age: int = Field(
        default=3600,
        description="Max sandbox age in seconds",
        validation_alias=AliasChoices(
            "WARM_POOL_MAX_AGE",
            "BASELINE_AGENT_CLI_WARM_POOL_MAX_AGE",
            "BASELINE_WARM_POOL_MAX_AGE",
        ),
    )
    warm_pool_max_requests: int = Field(
        default=10,
        description="Max requests per sandbox before refresh",
        validation_alias=AliasChoices(
            "WARM_POOL_MAX_REQUESTS",
            "BASELINE_AGENT_CLI_WARM_POOL_MAX_REQUESTS",
            "BASELINE_WARM_POOL_MAX_REQUESTS",
        ),
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
        default="tngtech/TNG-R1T-Chimera-Turbo",
        description="Fast model to use for routing decisions",
    )
    llm_routing_timeout: float = Field(
        default=3.0,
        description="Timeout in seconds for LLM routing check",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Log level",
        validation_alias=AliasChoices(
            "LOG_LEVEL",
            "BASELINE_AGENT_CLI_LOG_LEVEL",
            "BASELINE_LOG_LEVEL",
        ),
    )

    # E2E testing
    e2e_enabled: bool = Field(
        default=False,
        description="Enable end-to-end tests that hit deployed services",
        validation_alias=AliasChoices(
            "E2E_ENABLED",
            "BASELINE_AGENT_CLI_E2E_ENABLED",
            "BASELINE_E2E_ENABLED",
        ),
    )
    e2e_gateway_url: str = Field(
        default="https://janus-gateway-bqou.onrender.com",
        description="Gateway base URL for E2E tests",
        validation_alias=AliasChoices(
            "E2E_GATEWAY_URL",
            "BASELINE_AGENT_CLI_E2E_GATEWAY_URL",
            "BASELINE_E2E_GATEWAY_URL",
        ),
    )
    e2e_baseline_cli_url: str = Field(
        default="https://janus-baseline-agent.onrender.com",
        description="Baseline agent CLI base URL for E2E tests",
        validation_alias=AliasChoices(
            "E2E_BASELINE_CLI_URL",
            "BASELINE_AGENT_CLI_E2E_BASELINE_CLI_URL",
            "BASELINE_E2E_BASELINE_CLI_URL",
        ),
    )

    @property
    def effective_api_key(self) -> Optional[str]:
        """Get the API key for OpenAI-compatible calls."""
        return self.openai_api_key or self.chutes_api_key

    @property
    def chutes_api_base_effective(self) -> str:
        """Get the Chutes API base URL."""
        return self.openai_base_url or self.chutes_api_base

    @property
    def effective_api_base(self) -> str:
        """Get the API base URL (router or Chutes)."""
        if self.use_model_router:
            return f"http://{self.router_host}:{self.router_port}/v1"
        return self.chutes_api_base_effective

    @property
    def effective_model(self) -> str:
        """Get the effective model name."""
        if self.use_model_router:
            return "janus-router"
        return self.direct_model


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
