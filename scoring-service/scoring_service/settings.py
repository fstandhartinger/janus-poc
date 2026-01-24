from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCORING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./scoring.db",
        validation_alias="DATABASE_URL",
    )
    sandy_api_url: str = Field(
        default="https://sandbox.janus.rodeo",
        validation_alias="SANDY_API_URL",
    )
    judge_url: Optional[str] = Field(default=None, validation_alias="JUDGE_URL")
    judge_api_key: Optional[str] = Field(default=None, validation_alias="JUDGE_API_KEY")
    judge_model: str = Field(default="gpt-4o", validation_alias="JUDGE_MODEL")

    max_concurrent_runs: int = 5
    sse_poll_interval: float = 2.0
    run_rate_limit: int = 5
    run_rate_window_seconds: int = 60
    init_db: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
