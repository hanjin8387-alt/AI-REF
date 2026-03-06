from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping
from threading import Lock

LEGACY_AUTH_COUNTERS_TABLE = "legacy_auth_event_counters"
LEGACY_AUTH_COUNTERS_RPC = "increment_legacy_auth_event_counter"

logger = logging.getLogger(__name__)
_MEMORY_COUNTERS: Counter[str] = Counter()
_LOCK = Lock()


def _supports_rpc(db: object | None) -> bool:
    return db is not None and hasattr(db, "rpc")


def _supports_table(db: object | None) -> bool:
    return db is not None and hasattr(db, "table")


def _record_in_memory(*, outcome: str, reason: str) -> None:
    key = f"{outcome}:{reason}"
    with _LOCK:
        _MEMORY_COUNTERS[key] += 1


def record_legacy_auth_event(*, db: object | None = None, outcome: str, reason: str) -> None:
    _record_in_memory(outcome=outcome, reason=reason)
    logger.warning(
        "auth.legacy_app_token outcome=%s reason=%s",
        outcome,
        reason,
        extra={
            "event": "auth.legacy_app_token",
            "auth_mode": "legacy_app_token",
            "outcome": outcome,
            "reason": reason,
        },
    )

    if not _supports_rpc(db):
        return

    try:
        db.rpc(
            LEGACY_AUTH_COUNTERS_RPC,
            {
                "p_auth_mode": "legacy_app_token",
                "p_outcome": outcome,
                "p_reason": reason,
            },
        ).execute()
    except Exception:
        logger.warning(
            "legacy auth event persistence failed outcome=%s reason=%s",
            outcome,
            reason,
            exc_info=True,
        )


def get_legacy_auth_event_counts(*, db: object | None = None) -> dict[str, int]:
    if not _supports_table(db):
        with _LOCK:
            return dict(_MEMORY_COUNTERS)

    try:
        rows = (
            db.table(LEGACY_AUTH_COUNTERS_TABLE)
            .select("outcome,reason,event_count")
            .eq("auth_mode", "legacy_app_token")
            .order("event_count", desc=True)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.warning("legacy auth metrics load failed", exc_info=True)
        with _LOCK:
            return dict(_MEMORY_COUNTERS)

    counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        outcome = str(row.get("outcome") or "").strip()
        reason = str(row.get("reason") or "").strip()
        if not outcome or not reason:
            continue
        try:
            counts[f"{outcome}:{reason}"] = int(row.get("event_count") or 0)
        except (TypeError, ValueError):
            counts[f"{outcome}:{reason}"] = 0
    return counts


def reset_legacy_auth_event_counts(*, db: object | None = None) -> None:
    with _LOCK:
        _MEMORY_COUNTERS.clear()

    if not _supports_table(db):
        return

    try:
        db.table(LEGACY_AUTH_COUNTERS_TABLE).delete().eq("auth_mode", "legacy_app_token").execute()
    except Exception:
        logger.warning("legacy auth metrics reset failed", exc_info=True)
