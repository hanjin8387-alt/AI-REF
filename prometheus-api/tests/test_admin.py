import pytest
from fastapi import HTTPException, status

from app.api import admin
from app.core.config import get_settings


def test_require_admin_token_uses_timing_safe_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_compare_digest(left: str, right: str) -> bool:
        calls.append((left, right))
        return True

    monkeypatch.setattr(admin.secrets, "compare_digest", fake_compare_digest)
    admin._require_admin_token("test-app-token")

    assert calls == [("test-app-token", "test-app-token")]


def test_require_admin_token_rejects_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc:
        admin._require_admin_token("invalid-token")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_admin_token_rejects_when_server_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TOKEN", "")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        admin._require_admin_token("any-token")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
