from app.services.inventory_service import bulk_upsert_inventory


def test_bulk_upsert_uses_explicit_select_columns_and_name_filter(mock_supabase, monkeypatch) -> None:
    mock_supabase.tables["inventory"] = [
        {
            "id": "inv-1",
            "device_id": "device-1",
            "name": "Milk",
            "quantity": 1.0,
            "unit": "L",
            "expiry_date": None,
            "category": "냉장",
        },
        {
            "id": "inv-2",
            "device_id": "device-1",
            "name": "Rice",
            "quantity": 3.0,
            "unit": "kg",
            "expiry_date": None,
            "category": "상온",
        },
    ]

    seen_queries = []
    original_table = mock_supabase.table

    def recording_table(table_name: str):
        query = original_table(table_name)
        seen_queries.append(query)
        return query

    monkeypatch.setattr(mock_supabase, "table", recording_table)

    added_count, updated_count, items = bulk_upsert_inventory(
        mock_supabase,
        "device-1",
        [
            {"name": "Milk", "quantity": 1, "unit": "L"},
            {"name": "Egg", "quantity": 2, "unit": "ea"},
        ],
    )

    assert added_count == 1
    assert updated_count == 1
    assert sorted(item.name for item in items) == ["Egg", "Milk"]

    inventory_selects = [
        query for query in seen_queries if query._table_name == "inventory" and query._action == "select"
    ]
    assert inventory_selects
    first_select = inventory_selects[0]
    assert first_select._columns == ["id", "name", "quantity", "unit", "expiry_date", "category"]
    assert ("in", "name", ["Milk", "Egg"]) in first_select._filters


def test_bulk_upsert_merges_existing_quantity(mock_supabase) -> None:
    mock_supabase.tables["inventory"] = [
        {
            "id": "inv-1",
            "device_id": "device-1",
            "name": "Milk",
            "quantity": 1.5,
            "unit": "L",
            "expiry_date": None,
            "category": "냉장",
        }
    ]

    added_count, updated_count, items = bulk_upsert_inventory(
        mock_supabase,
        "device-1",
        [{"name": "Milk", "quantity": 0.5, "unit": "L"}],
    )

    assert added_count == 0
    assert updated_count == 1
    assert len(items) == 1
    assert items[0].name == "Milk"
    assert items[0].quantity == 2.0


def test_bulk_upsert_returns_empty_for_empty_input(mock_supabase) -> None:
    added_count, updated_count, items = bulk_upsert_inventory(mock_supabase, "device-1", [])

    assert added_count == 0
    assert updated_count == 0
    assert items == []


def test_bulk_upsert_uses_earliest_expiry_for_same_item(mock_supabase) -> None:
    added_count, updated_count, items = bulk_upsert_inventory(
        mock_supabase,
        "device-1",
        [
            {"name": "Apple", "quantity": 1, "unit": "ea", "expiry_date": "2026-02-20"},
            {"name": "apple", "quantity": 1, "unit": "ea", "expiry_date": "2026-02-18"},
        ],
    )

    assert added_count == 1
    assert updated_count == 0
    assert len(items) == 1
    assert items[0].name == "Apple"
    assert items[0].quantity == 2.0
    assert items[0].expiry_date is not None
    assert items[0].expiry_date.date().isoformat() == "2026-02-18"
