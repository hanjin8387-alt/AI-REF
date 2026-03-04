from __future__ import annotations

from supabase import Client

from ..schemas.schemas import InventoryItem, LowStockSuggestionItem, ShoppingItemInput, ShoppingItemSource, ShoppingItemStatus
from ..services.inventory_service import bulk_upsert_inventory


def normalize_name(value: str) -> str:
    return value.strip().lower()


def normalize_unit(value: str | None) -> str:
    unit = (value or "").strip()
    if not unit:
        return "개"
    if unit.lower() == "unit":
        return "개"
    return unit


def parse_quantity(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def aggregate_shopping_items(items: list[ShoppingItemInput]) -> dict[str, dict]:
    aggregated: dict[str, dict] = {}
    for item in items:
        name = item.name.strip()
        if not name:
            continue
        quantity = max(float(item.quantity), 0.0)
        if quantity <= 0:
            continue

        key = normalize_name(name)
        payload = aggregated.setdefault(
            key,
            {
                "name": name,
                "quantity": 0.0,
                "unit": normalize_unit(item.unit),
            },
        )
        payload["quantity"] += quantity
        if item.unit and item.unit.strip():
            payload["unit"] = normalize_unit(item.unit)

    for payload in aggregated.values():
        payload["quantity"] = round(payload["quantity"], 2)
    return aggregated


def upsert_pending_shopping_items(
    db: Client,
    device_id: str,
    aggregated: dict[str, dict],
    source: ShoppingItemSource,
    recipe_id: str | None,
    recipe_title: str | None,
) -> tuple[int, int, list[dict]]:
    if not aggregated:
        return 0, 0, []

    existing_rows = (
        db.table("shopping_items")
        .select("id,name,quantity,unit")
        .eq("device_id", device_id)
        .eq("status", ShoppingItemStatus.PENDING.value)
        .execute()
        .data
        or []
    )
    existing_by_name = {str(row.get("name", "")).strip().lower(): row for row in existing_rows}

    added_count = 0
    updated_count = 0
    update_rows: list[dict] = []
    insert_rows: list[dict] = []

    for key, payload in aggregated.items():
        existing = existing_by_name.get(key)
        if existing:
            current_qty = parse_quantity(existing.get("quantity"))
            new_quantity = round(current_qty + payload["quantity"], 2)
            update_row: dict[str, object] = {
                "id": existing["id"],
                "device_id": device_id,
                "quantity": new_quantity,
                "unit": payload["unit"] or normalize_unit(str(existing.get("unit") or "")),
            }
            if source != ShoppingItemSource.MANUAL:
                update_row["source"] = source.value
            if recipe_id:
                update_row["recipe_id"] = recipe_id
            if recipe_title:
                update_row["recipe_title"] = recipe_title

            update_rows.append(update_row)
            updated_count += 1
            continue

        insert_rows.append(
            {
                "device_id": device_id,
                "name": payload["name"],
                "quantity": payload["quantity"],
                "unit": payload["unit"],
                "status": ShoppingItemStatus.PENDING.value,
                "source": source.value,
                "recipe_id": recipe_id,
                "recipe_title": recipe_title,
                "added_to_inventory": False,
            }
        )
        added_count += 1

    touched_rows: list[dict] = []
    if update_rows:
        updated = db.table("shopping_items").upsert(update_rows, on_conflict="id").execute()
        touched_rows.extend(updated.data or [])
    if insert_rows:
        inserted = db.table("shopping_items").insert(insert_rows).execute()
        touched_rows.extend(inserted.data or [])

    return added_count, updated_count, touched_rows


def apply_inventory_from_shopping(
    db: Client,
    device_id: str,
    shopping_rows: list[dict],
) -> tuple[int, int, list[InventoryItem]]:
    raw_items = []
    for row in shopping_rows:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        quantity = max(parse_quantity(row.get("quantity")), 0.0)
        if quantity <= 0:
            continue
        raw_items.append(
            {
                "name": name,
                "quantity": quantity,
                "unit": normalize_unit(str(row.get("unit") or "")),
            }
        )

    return bulk_upsert_inventory(db, device_id, raw_items)


def build_low_stock_suggestions(
    inventory_rows: list[dict],
    consumption_rows: list[dict],
    pending_shopping_rows: list[dict],
    lookback_days: int,
    threshold_days: int,
) -> list[LowStockSuggestionItem]:
    pending_names = {str(row.get("name", "")).strip().lower() for row in pending_shopping_rows}

    daily_usage_by_name: dict[str, float] = {}
    for row in consumption_rows:
        if str(row.get("action", "")).lower() != "cook":
            continue
        item_name = str(row.get("item_name", "")).strip().lower()
        if not item_name:
            continue
        qty = abs(parse_quantity(row.get("quantity_change")))
        if qty <= 0:
            continue
        daily_usage_by_name[item_name] = daily_usage_by_name.get(item_name, 0.0) + (qty / max(1, lookback_days))

    suggestions: list[LowStockSuggestionItem] = []
    for row in inventory_rows:
        item_name_raw = str(row.get("name", "")).strip()
        item_name = item_name_raw.lower()
        if not item_name or item_name in pending_names:
            continue

        current_qty = max(parse_quantity(row.get("quantity")), 0.0)
        if current_qty <= 0:
            continue

        daily_usage = daily_usage_by_name.get(item_name, 0.0)
        if daily_usage <= 0:
            continue

        predicted_days = round(current_qty / daily_usage, 1)
        if predicted_days > threshold_days:
            continue

        recommended_qty = max(round((daily_usage * 7) - current_qty, 2), 1.0)
        suggestions.append(
            LowStockSuggestionItem(
                name=item_name_raw,
                current_quantity=round(current_qty, 2),
                unit=normalize_unit(str(row.get("unit") or "")),
                predicted_days_left=predicted_days,
                recommended_quantity=recommended_qty,
            )
        )

    suggestions.sort(key=lambda item: item.predicted_days_left)
    return suggestions
