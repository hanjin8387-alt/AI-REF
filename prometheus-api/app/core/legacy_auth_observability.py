from __future__ import annotations

from supabase import Client

from .database import get_supabase_client
from ..services.auth.legacy_metrics import (
    get_legacy_auth_event_counts as _get_legacy_auth_event_counts,
    record_legacy_auth_event as _record_legacy_auth_event,
    reset_legacy_auth_event_counts as _reset_legacy_auth_event_counts,
)


def get_legacy_auth_event_counts(db: Client | None = None) -> dict[str, int]:
    if db is None:
        db = get_supabase_client()
    return _get_legacy_auth_event_counts(db=db)


def record_legacy_auth_event(*, db: Client | None = None, outcome: str, reason: str) -> None:
    _record_legacy_auth_event(db=db, outcome=outcome, reason=reason)


def reset_legacy_auth_event_counts(db: Client | None = None) -> None:
    _reset_legacy_auth_event_counts(db=db)
