from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import app.core.security as security_module
from app.api.admin import get_legacy_auth_metrics
from app.core.security import require_app_token
from app.services.auth.legacy_metrics import get_legacy_auth_event_counts, record_legacy_auth_event

from .fakes import FakeDB


def _capture_legacy_event(events: list[tuple[str, str]]):
    def recorder(*, db=None, outcome: str, reason: str) -> None:
        events.append((outcome, reason))

    return recorder


def test_rejects_legacy_only_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(security_module, "record_legacy_auth_event", _capture_legacy_event(events))

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "X-App-ID header is required"
    assert events == [("rejected", "compat_disabled")]


def test_accepts_legacy_only_when_compatibility_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.setenv("APP_TOKEN", "legacy-token")
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(security_module, "record_legacy_auth_event", _capture_legacy_event(events))

    require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert events == [("accepted", "legacy_compat")]


def test_rejects_legacy_only_with_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.setenv("APP_TOKEN", "legacy-token")
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(security_module, "record_legacy_auth_event", _capture_legacy_event(events))

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="wrong-token")

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid app token"
    assert events == [("rejected", "invalid_token")]


def test_legacy_mode_unconfigured_server_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app")
    monkeypatch.setenv("ALLOW_LEGACY_APP_TOKEN", "true")
    monkeypatch.delenv("APP_TOKEN", raising=False)
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(security_module, "record_legacy_auth_event", _capture_legacy_event(events))

    with pytest.raises(HTTPException) as excinfo:
        require_app_token(x_app_id=None, x_app_token="legacy-token")

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Server legacy APP_TOKEN is not configured"
    assert events == [("rejected", "server_unconfigured")]


def test_app_id_auth_succeeds_without_legacy_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_IDS", "prometheus-app,prometheus-web")
    events: list[tuple[str, str]] = []
    monkeypatch.setattr(security_module, "record_legacy_auth_event", _capture_legacy_event(events))

    require_app_token(x_app_id="prometheus-app", x_app_token=None)

    assert events == []


def test_legacy_metrics_use_durable_counter_table_when_db_is_available() -> None:
    db = FakeDB({"legacy_auth_event_counters": []})

    record_legacy_auth_event(db=db, outcome="accepted", reason="legacy_compat")
    record_legacy_auth_event(db=db, outcome="accepted", reason="legacy_compat")
    record_legacy_auth_event(db=db, outcome="rejected", reason="invalid_token")

    assert get_legacy_auth_event_counts(db=db) == {
        "accepted:legacy_compat": 2,
        "rejected:invalid_token": 1,
    }


def test_legacy_metrics_raise_when_durable_store_is_unavailable() -> None:
    with pytest.raises(RuntimeError):
        get_legacy_auth_event_counts(db=None)


def test_admin_legacy_metrics_reads_durable_counts_only() -> None:
    async def run() -> None:
        db = FakeDB({"legacy_auth_event_counters": []})
        record_legacy_auth_event(db=db, outcome="accepted", reason="legacy_compat")

        payload = await get_legacy_auth_metrics(_=None, db=db)

        assert payload == {
            "legacy_auth_events": {
                "accepted:legacy_compat": 1,
            }
        }

    asyncio.run(run())
