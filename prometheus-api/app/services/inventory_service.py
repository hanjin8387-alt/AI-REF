"""Shared inventory upsert logic used by both inventory and shopping modules."""
from datetime import datetime
import logging
from typing import Any

from supabase import Client

from ..schemas.schemas import InventoryItem

logger = logging.getLogger(__name__)


def _to_iso_date(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def bulk_upsert_inventory(
    db: Client,
    device_id: str,
    items: list[dict],
) -> tuple[int, int, list[InventoryItem]]:
    """Merge items into existing inventory.

    Each item dict should have: name, quantity, unit.
    Optional: expiry_date, category.

    Returns (added_count, updated_count, inventory_items).
    """
    if not items:
        return 0, 0, []

    # Aggregate by lowercase name
    aggregated: dict[str, dict] = {}
    for raw_item in items:
        name = str(raw_item.get("name", "")).strip()
        if not name:
            continue

        key = name.lower()
        payload = aggregated.setdefault(
            key,
            {
                "name": name,
                "quantity": 0.0,
                "unit": (str(raw_item.get("unit") or "unit")).strip() or "unit",
                "expiry_date": None,
                "category": raw_item.get("category"),
            },
        )
        payload["quantity"] += max(float(raw_item.get("quantity", 0)), 0.0)
        unit = str(raw_item.get("unit") or "").strip()
        if unit:
            payload["unit"] = unit
        expiry = raw_item.get("expiry_date")
        if expiry:
            current = payload["expiry_date"]
            if current is None or expiry < current:
                payload["expiry_date"] = expiry

    if not aggregated:
        return 0, 0, []

    input_names = [str(payload["name"]).strip() for payload in aggregated.values() if str(payload["name"]).strip()]

    # Fetch existing inventory
    existing_query = (
        db.table("inventory")
        .select("id,name,quantity,unit,expiry_date,category")
        .eq("device_id", device_id)
    )
    if input_names:
        existing_query = existing_query.in_("name", input_names)
    existing_rows = existing_query.execute().data or []
    existing_by_name = {str(row["name"]).strip().lower(): row for row in existing_rows}

    upsert_rows: list[dict] = []
    added_count = 0
    updated_count = 0
    touched_names: list[str] = []
    log_entries: list[dict] = []

    for key, payload in aggregated.items():
        existing = existing_by_name.get(key)
        existing_qty = float(existing.get("quantity", 0)) if existing else 0.0
        new_quantity = round(existing_qty + payload["quantity"], 2)
        if new_quantity <= 0:
            continue

        row_name = str(existing["name"]).strip() if existing else payload["name"]
        touched_names.append(row_name)
        upsert_rows.append(
            {
                "device_id": device_id,
                "name": row_name,
                "quantity": new_quantity,
                "unit": payload["unit"]
                or (existing.get("unit") if existing else "unit")
                or "unit",
                "expiry_date": _to_iso_date(payload["expiry_date"])
                or (existing.get("expiry_date") if existing else None),
                "category": payload.get("category")
                or (existing.get("category") if existing else None),
            }
        )

        action = "update" if existing else "add"
        if existing:
            updated_count += 1
        else:
            added_count += 1

        log_entries.append(
            {
                "device_id": device_id,
                "item_name": row_name,
                "action": action,
                "quantity_change": round(payload["quantity"], 2),
                "metadata": {"previous_quantity": existing_qty, "new_quantity": new_quantity},
            }
        )

    if not upsert_rows:
        return 0, 0, []

    db.table("inventory").upsert(upsert_rows, on_conflict="device_id,name").execute()

    # Log inventory changes (best-effort)
    _write_inventory_logs(db, log_entries)

    refreshed_rows = (
        db.table("inventory")
        .select("id,name,quantity,unit,expiry_date,category")
        .eq("device_id", device_id)
        .in_("name", touched_names)
        .execute()
        .data
        or []
    )
    items_out = [InventoryItem(**row) for row in refreshed_rows]
    return added_count, updated_count, items_out


def log_inventory_change(
    db: Client,
    device_id: str,
    item_name: str,
    action: str,
    quantity_change: float = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a single inventory change log entry (best-effort)."""
    _write_inventory_logs(
        db,
        [
            {
                "device_id": device_id,
                "item_name": item_name,
                "action": action,
                "quantity_change": round(quantity_change, 2),
                "metadata": metadata or {},
            }
        ],
    )


def _write_inventory_logs(db: Client, entries: list[dict]) -> None:
    if not entries:
        return
    try:
        db.table("inventory_logs").insert(entries).execute()
    except Exception:
        logger.warning("inventory_logs insert failed count=%s (best-effort)", len(entries), exc_info=True)
