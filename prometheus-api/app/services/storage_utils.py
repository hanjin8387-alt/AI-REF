from __future__ import annotations

STORAGE_CATEGORIES = ("냉장", "냉동", "상온")


def normalize_storage_category(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().casefold().replace("_", "").replace("-", "").replace(" ", "")
    if not normalized:
        return None

    alias_map = {
        "냉장": "냉장",
        "refrigerated": "냉장",
        "refrigerator": "냉장",
        "fridge": "냉장",
        "chill": "냉장",
        "cold": "냉장",
        "냉동": "냉동",
        "frozen": "냉동",
        "freezer": "냉동",
        "freeze": "냉동",
        "상온": "상온",
        "실온": "상온",
        "ambient": "상온",
        "pantry": "상온",
        "roomtemperature": "상온",
    }
    mapped = alias_map.get(normalized)
    if mapped:
        return mapped

    if any(token in normalized for token in ("냉동", "freezer", "frozen", "freeze")):
        return "냉동"
    if any(token in normalized for token in ("냉장", "fridge", "refriger", "chill", "cold")):
        return "냉장"
    if any(token in normalized for token in ("상온", "실온", "ambient", "pantry", "roomtemperature")):
        return "상온"
    return None


def guess_storage_from_name(name: str) -> str:
    lowered = (name or "").lower()

    frozen_keywords = ["냉동", "ice", "frozen", "만두", "피자", "아이스", "새우", "튀김"]
    chilled_keywords = [
        "우유",
        "치즈",
        "요거트",
        "계란",
        "두부",
        "고기",
        "생선",
        "버터",
        "크림",
        "채소",
        "과일",
        "meat",
        "fish",
        "milk",
        "egg",
        "cheese",
        "yogurt",
        "tofu",
    ]

    if any(keyword in lowered for keyword in frozen_keywords):
        return "냉동"
    if any(keyword in lowered for keyword in chilled_keywords):
        return "냉장"
    return "상온"
