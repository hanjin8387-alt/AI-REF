from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.legacy_auth_observability import reset_legacy_auth_event_counts


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(Path(__file__).resolve().parent)

    for key in [
        "ALLOW_LEGACY_APP_TOKEN",
        "APP_TOKEN",
        "APP_IDS",
        "GEMINI_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()
    reset_legacy_auth_event_counts()
    yield
    get_settings.cache_clear()
    reset_legacy_auth_event_counts()
