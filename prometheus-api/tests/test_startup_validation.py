from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.startup_validation import validate_startup_settings


def test_production_like_rejects_placeholder_admin_token() -> None:
  settings = Settings(
    environment='production',
    app_ids='prometheus-app',
    admin_token='change-this-admin-token',
    supabase_url='https://example.supabase.co',
    supabase_key='service-role',
    gemini_api_key='gemini-key',
  )

  with pytest.raises(RuntimeError) as excinfo:
    validate_startup_settings(settings)

  assert 'ADMIN_TOKEN' in str(excinfo.value)


def test_development_allows_placeholder_admin_token() -> None:
  settings = Settings(
    environment='development',
    app_ids='prometheus-app',
    admin_token='change-this-admin-token',
    supabase_url='https://example.supabase.co',
    supabase_key='service-role',
    gemini_api_key='gemini-key',
  )

  validate_startup_settings(settings)
