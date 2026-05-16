from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Mimic"
    environment: Literal["local", "production", "test"] = "local"
    debug: bool = Field(default=False, alias="APP_DEBUG")

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")

    database_url: str = Field(
        default="postgresql+asyncpg://mimic:mimic@localhost:5432/mimic",
        alias="DATABASE_URL",
    )

    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_MODEL")
    llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")
    ai_quality_threshold: int = Field(default=75, alias="AI_QUALITY_THRESHOLD")

    free_generations_limit: int = Field(default=3, alias="FREE_GENERATIONS_LIMIT")
    free_generations_period: Literal["monthly", "all_time"] = Field(
        default="monthly",
        alias="FREE_GENERATIONS_PERIOD",
    )
    start_generations_limit: int = Field(default=50, alias="START_GENERATIONS_LIMIT")

    default_timezone: str = Field(default="Europe/Moscow", alias="DEFAULT_TIMEZONE")
    default_daily_post_time: str = Field(default="12:00", alias="DEFAULT_DAILY_POST_TIME")

    admin_session_secret: str = Field(default="change-me", alias="ADMIN_SESSION_SECRET")
    admin_login: str = Field(default="admin", alias="ADMIN_LOGIN")
    admin_password: str = Field(default="admin", alias="ADMIN_PASSWORD")

    prompts_dir: Path = Field(default=Path("prompts"), alias="PROMPTS_DIR")

    @property
    def admin_ids(self) -> set[int]:
        ids: set[int] = set()
        for raw_id in self.admin_telegram_ids.split(","):
            raw_id = raw_id.strip()
            if raw_id.isdigit():
                ids.add(int(raw_id))
        return ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
