from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    app_name: str = "PROMETHEUS API"
    debug: bool = False
    environment: str = "development"
    app_ids: str = "prometheus-app,prometheus-web"
    allow_legacy_app_token: bool = True
    require_app_token: bool = False
    app_token: str = ""
    admin_token: str = ""
    cors_origins: str = "http://localhost:8081,http://localhost:19006,http://localhost:3000"
    allowed_device_ids: str = ""
    device_token_ttl_hours: int = 720

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Limits
    max_upload_size_mb: int = 8
    recipe_cache_ttl_minutes: int = 30

    # Cache
    cache_backend: str = "auto"  # auto | memory | redis
    redis_url: Optional[str] = None

    # Language
    default_language: str = "ko"  # ko | en | ja

    # Barcode / Open Food Facts
    open_food_facts_enabled: bool = True

    # Firebase
    firebase_credentials: Optional[str] = None

    @property
    def parsed_cors_origins(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.environment.lower() in {"production", "prod", "staging", "stage"}

    @property
    def parsed_allowed_device_ids(self) -> set[str]:
        raw = self.allowed_device_ids.strip()
        if not raw:
            return set()
        return {item.strip() for item in raw.split(",") if item.strip()}

    @property
    def parsed_app_ids(self) -> set[str]:
        raw = self.app_ids.strip()
        if not raw:
            return set()
        return {item.strip().lower() for item in raw.split(",") if item.strip()}

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
