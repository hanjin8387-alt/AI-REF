import pytest
from fastapi import HTTPException, status

from app.api.admin import _require_admin_token
from app.core.config import get_settings
from app.core.security import get_device_id, require_app_token


def test_require_app_token_accepts_valid_token() -> None:
    require_app_token("test-app-token")


def test_require_app_token_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc:
        require_app_token(None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_require_app_token_rejects_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc:
        require_app_token("invalid-token")
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_device_id_accepts_valid_id() -> None:
    assert get_device_id("device-1234") == "device-1234"


def test_get_device_id_rejects_too_short_id() -> None:
    with pytest.raises(HTTPException) as exc:
        get_device_id("short")
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


def test_get_device_id_rejects_too_long_id() -> None:
    with pytest.raises(HTTPException) as exc:
        get_device_id("a" * 129)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


def test_get_device_id_rejects_non_whitelisted_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_DEVICE_IDS", "allowed-1234,allowed-5678")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        get_device_id("blocked-0000")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_get_device_id_accepts_whitelisted_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_DEVICE_IDS", "allowed-1234,allowed-5678")
    get_settings.cache_clear()

    assert get_device_id("allowed-5678") == "allowed-5678"


def test_require_admin_token_accepts_valid_token() -> None:
    _require_admin_token("test-admin-token")


def test_require_admin_token_rejects_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc:
        _require_admin_token("invalid-token")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
