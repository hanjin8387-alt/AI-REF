from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import require_app_token, require_device_auth


def test_require_app_token_accepts_known_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app,prometheus-web")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "false")
    get_settings.cache_clear()
    require_app_token("prometheus-app", None)


def test_require_app_token_rejects_unknown_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "false")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        require_app_token("unknown-app", None)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_app_token_accepts_legacy_token_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.setenv("REQUIRE_APP_TOKEN", "true")
    monkeypatch.setenv("APP_TOKEN", "legacy-token")
    get_settings.cache_clear()
    require_app_token(None, "legacy-token")


def test_require_device_auth_rejects_expired_token(mock_supabase, seed_supabase) -> None:
    token = "expired-token"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    seed_supabase(
        "devices",
        [
            {
                "device_id": "device-1234",
                "device_secret_hash": token_hash,
                "token_version": 1,
                "token_expires_at": "2000-01-01T00:00:00+00:00",
                "token_revoked_at": None,
                "last_used_at": None,
            }
        ],
    )

    with pytest.raises(HTTPException) as exc:
        require_device_auth(device_id="device-1234", db=mock_supabase, x_device_token=token)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
