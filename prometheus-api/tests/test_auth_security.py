from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.legacy_auth_observability import get_legacy_auth_event_counts
from app.core.security import require_app_token


def test_rejects_legacy_only_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "X-App-ID header is required"
    assert get_legacy_auth_event_counts() == {"rejected:compat_disabled": 1}


def test_accepts_legacy_only_when_compatibility_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.setenv("APP_TOKEN", "legacy-token")

    require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert get_legacy_auth_event_counts() == {"accepted:legacy_compat": 1}


def test_rejects_legacy_only_with_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.setenv("APP_TOKEN", "legacy-token")

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="wrong-token")

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid app token"
    assert get_legacy_auth_event_counts() == {"rejected:invalid_token": 1}


def test_legacy_mode_unconfigured_server_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.delenv("APP_TOKEN", raising=False)

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Server legacy APP_TOKEN is not configured"
    assert get_legacy_auth_event_counts() == {"rejected:server_unconfigured": 1}


def test_app_id_auth_succeeds_without_legacy_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app,prometheus-web")

    require_app_token(x_app_id="prometheus-app", x_app_token=None)

    assert get_legacy_auth_event_counts() == {}
