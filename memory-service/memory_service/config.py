from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./memory.db",
        validation_alias="DATABASE_URL",
    )
    chutes_api_key: str = Field(default="", validation_alias="CHUTES_API_KEY")

    llm_base_url: str = "https://llm.chutes.ai/v1"
    llm_model: str = "GLM-4-9B-0414-fast"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1000
    llm_timeout_seconds: float = 30.0

    max_memories_per_user: int = 100
    rate_limit_per_minute: int = 60
    rate_limit_window_seconds: int = 60

    init_db: bool = False
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
