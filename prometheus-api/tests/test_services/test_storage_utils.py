from app.services.storage_utils import guess_storage_from_name, normalize_storage_category


def test_normalize_storage_category_maps_common_aliases() -> None:
    assert normalize_storage_category("refrigerator") == "냉장"
    assert normalize_storage_category("freezer") == "냉동"
    assert normalize_storage_category("room temperature") == "상온"


def test_normalize_storage_category_returns_none_for_unknown_values() -> None:
    assert normalize_storage_category("mystery-zone") is None
    assert normalize_storage_category("") is None
    assert normalize_storage_category(None) is None


def test_guess_storage_from_name_uses_keyword_heuristics() -> None:
    assert guess_storage_from_name("냉동만두") == "냉동"
    assert guess_storage_from_name("우유") == "냉장"
    assert guess_storage_from_name("쌀") == "상온"
