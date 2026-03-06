from __future__ import annotations

DEFAULT_UNIT = "\uAC1C"
LEGACY_DEFAULT_UNIT = "unit"


def normalize_unit(value: str | None, *, fallback: str = DEFAULT_UNIT) -> str:
    unit = str(value or "").strip()
    if not unit:
        return fallback
    if unit.casefold() == LEGACY_DEFAULT_UNIT:
        return fallback
    return unit


def normalize_default_unit(value: str | None) -> str:
    return normalize_unit(value)
