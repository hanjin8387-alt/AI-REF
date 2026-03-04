from __future__ import annotations

import logging
from collections import Counter
from threading import Lock

logger = logging.getLogger(__name__)

_LEGACY_AUTH_EVENTS: Counter[str] = Counter()
_LOCK = Lock()


def record_legacy_auth_event(*, outcome: str, reason: str) -> None:
    """Record and log legacy token usage events for migration observability."""
    key = f"{outcome}:{reason}"
    with _LOCK:
        _LEGACY_AUTH_EVENTS[key] += 1

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


def get_legacy_auth_event_counts() -> dict[str, int]:
    with _LOCK:
        return dict(_LEGACY_AUTH_EVENTS)


def reset_legacy_auth_event_counts() -> None:
    with _LOCK:
        _LEGACY_AUTH_EVENTS.clear()
