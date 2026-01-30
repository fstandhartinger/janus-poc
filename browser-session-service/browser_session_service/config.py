"""Configuration for the browser session service."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="SESSION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./sessions.db",
        validation_alias="DATABASE_URL",
    )

    # Encryption - 32 bytes base64-encoded secret for AES-256
    encryption_secret: str = Field(
        default="",
        validation_alias="SESSION_ENCRYPTION_SECRET",
        description="Base64-encoded 32-byte secret for AES-256-GCM encryption",
    )

    # Chutes IDP for JWT validation
    chutes_idp_jwks_url: str = Field(
        default="https://idp.chutes.ai/.well-known/jwks.json",
        validation_alias="CHUTES_IDP_JWKS_URL",
    )
    chutes_idp_issuer: str = Field(
        default="https://idp.chutes.ai",
        validation_alias="CHUTES_IDP_ISSUER",
    )
    chutes_idp_audience: str = Field(
        default="janus",
        validation_alias="CHUTES_IDP_AUDIENCE",
    )

    # Validation limits
    max_session_name_length: int = 50
    max_description_length: int = 500
    max_domains_per_session: int = 10
    max_storage_state_bytes: int = 1024 * 1024  # 1MB

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_window_seconds: int = 60

    # Database initialization
    init_db: bool = False
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
