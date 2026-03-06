from __future__ import annotations

from .config import Settings

MIN_ADMIN_TOKEN_LENGTH = 24
_WEAK_ADMIN_TOKENS = {
    "",
    "admin",
    "changeme",
    "change-this-admin-token",
    "default",
    "example",
    "password",
    "placeholder",
    "replace-me",
    "test",
}


def is_weak_admin_token(value: str | None) -> bool:
    token = (value or "").strip()
    if not token:
        return True

    lowered = token.casefold()
    if lowered in _WEAK_ADMIN_TOKENS:
        return True
    if "change-this" in lowered or "replace" in lowered:
        return True
    return len(token) < MIN_ADMIN_TOKEN_LENGTH


def validate_startup_settings(settings: Settings) -> None:
    missing: list[str] = []
    if settings.allow_legacy_app_token and not settings.app_token:
        missing.append("APP_TOKEN")
    if settings.is_production_like and not settings.admin_token:
        missing.append("ADMIN_TOKEN")
    if not settings.supabase_url:
        missing.append("SUPABASE_URL")
    if not settings.supabase_key:
        missing.append("SUPABASE_KEY")
    if not settings.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not settings.parsed_app_ids:
        missing.append("APP_IDS")

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    if not settings.parsed_cors_origins:
        raise RuntimeError("CORS_ORIGINS must include at least one explicit origin")
    if settings.is_production_like and settings.cors_origins.strip() == "*":
        raise RuntimeError("CORS_ORIGINS must not be '*' in production-like environments")
    if settings.is_production_like and is_weak_admin_token(settings.admin_token):
        raise RuntimeError("ADMIN_TOKEN must be a strong non-placeholder secret in a production-like environment")
