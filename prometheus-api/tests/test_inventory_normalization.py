from __future__ import annotations

from app.core.normalization import normalize_item_name
from app.services.inventory_service import bulk_upsert_inventory


def test_normalize_item_name_casefold_and_whitespace() -> None:
    assert normalize_item_name("  Milk   Powder ") == "milk powder"


def test_bulk_upsert_uses_name_normalized_conflict(mock_supabase, seed_supabase) -> None:
    seed_supabase(
        "inventory",
        [
            {
                "id": "inv-1",
                "device_id": "device-1234",
                "name": "Milk",
                "name_normalized": "milk",
                "quantity": 1.0,
                "unit": "개",
                "expiry_date": None,
                "category": "냉장",
            }
        ],
    )

    added_count, updated_count, items = bulk_upsert_inventory(
        mock_supabase,
        "device-1234",
        [{"name": "  milk ", "quantity": 2, "unit": "개", "category": "fridge"}],
    )

    assert added_count == 0
    assert updated_count == 1
    assert len(items) == 1
    assert items[0].name_normalized == "milk"
    assert float(items[0].quantity) == 3.0
