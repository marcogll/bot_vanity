from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 8000
    debug: bool = False
    env: str = "production"

    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance_name: str = "vanity-instance"

    openai_api_key: str = Field(..., min_length=1)
    llm_model: str = "gpt-4o"

    database_url: str = Field(..., min_length=1)
    aes_encryption_key: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("AES_ENCRYPTION_KEY", "ENCRYPTION_KEY"),
    )
    memory_retention_days: int = 30
    webhook_secret: str = Field(..., min_length=1)
    rate_limit_max_requests: int = 20
    rate_limit_window_seconds: int = 60
    follow_up_delay_seconds: int = 600
    janitor_interval_seconds: int = 86_400

    booking_url: str = "https://vanitynails.fresh.com"
    docs_path: str = "docs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
