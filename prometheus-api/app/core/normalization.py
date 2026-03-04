from __future__ import annotations

import unicodedata


def normalize_item_name(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    compact = " ".join(text.split())
    normalized = unicodedata.normalize("NFKC", compact)
    return normalized.casefold()
