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
    evolution_connected_number: str = ""

    openai_api_key: str = Field(..., min_length=1)
    llm_model: str = "gpt-4o"
    audio_transcription_model: str = "gpt-4o-mini-transcribe"

    database_url: str = Field(..., min_length=1)
    aes_encryption_key: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("AES_ENCRYPTION_KEY", "ENCRYPTION_KEY"),
    )
    memory_retention_days: int = 30
    webhook_secret: str = Field(..., min_length=1)
    admin_phone_number: str = ""
    admin_phone_numbers: str = ""
    memory_delete_trigger: str = "dipiridú"
    rate_limit_max_requests: int = 20
    rate_limit_window_seconds: int = 60
    follow_up_delay_seconds: int = 900
    janitor_interval_seconds: int = 86_400
    test_mode_enabled: bool = True
    test_mode_allowed_numbers: str = ""
    test_mode_export_webhook_url: str = ""
    test_mode_export_webhook_auth_header: str = "Authorization"
    test_mode_export_webhook_auth_value: str = ""
    test_mode_session_minutes: int = 15
    bot_runtime_v2_enabled: bool = False
    bot_runtime_v2_shadow_mode: bool = False
    bot_runtime_v2_allowed_numbers: str = ""
    role_blend_enabled: bool = False
    tenant_config_path: str = "tenants"
    default_tenant_id: str = "vanity"

    booking_url: str = "https://vanitynails.fresh.com"
    ios_app_store_url: str = "https://apps.apple.com/app/id1297230801"
    android_play_store_url: str = "https://play.google.com/store/apps/details?id=com.fresha.Fresha"
    payment_url: str = "https://www.paypal.com/ncp/payment/L3AC4D47J3QDN"
    docs_path: str = "docs"
    fresha_service_csv_path: str = "export_service_list_2026-05-11.csv"
    admin_webui_enabled: bool = True
    admin_bootstrap_username: str = "admin"
    admin_bootstrap_password: str = ""
    admin_bootstrap_reset_existing: bool = False
    admin_session_cookie_name: str = "sofia_admin_session"
    admin_session_minutes: int = 120
    admin_session_secret: str = ""
    admin_login_max_attempts: int = 5
    admin_lockout_minutes: int = 15

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
