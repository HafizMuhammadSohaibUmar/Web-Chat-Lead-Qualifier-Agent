"""Application configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    business_id: str = "default-business"
    business_name: str = "Acme Home Services"
    business_type: str = "home services"
    business_phone: str = "+15551234567"
    allowed_origins: str = "http://localhost:8005"

    host: str = "0.0.0.0"
    port: int = 8005
    public_base_url: str = "http://localhost:8005"
    log_level: str = "INFO"

    jwt_secret: str = "change_me_widget_session_secret"
    jwt_algorithm: str = "HS256"
    session_expiry_minutes: int = 30
    max_messages_per_session: int = 30
    max_sessions_per_business_day: int = 100
    max_messages_per_ip_minute: int = 20

    supabase_url: str = ""
    supabase_key: str = ""

    gemini_api_key: str = ""
    mistral_api_key: str = ""
    primary_model: str = "gemini/gemini-2.5-flash"
    fallback_model: str = "mistral/mistral-small-latest"
    llm_timeout_seconds: float = 8.0

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    owner_phone_number: str = ""
    sms_dry_run: bool = True

    admin_api_key: str = "change_me_admin_key"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    demo_mode_enabled: bool = True

    @property
    def origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
