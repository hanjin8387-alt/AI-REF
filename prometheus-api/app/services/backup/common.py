from __future__ import annotations

from fastapi import HTTPException, status

from ...core.db_columns import (
    COOKING_HISTORY_SELECT_COLUMNS,
    FAVORITE_RECIPE_SELECT_COLUMNS,
    INVENTORY_LOG_SELECT_COLUMNS,
    INVENTORY_SELECT_COLUMNS,
    NOTIFICATION_SELECT_COLUMNS,
    PRICE_HISTORY_SELECT_COLUMNS,
    SHOPPING_ITEM_SELECT_COLUMNS,
)
from ...core.normalization import NAME_NORMALIZATION_VERSION, normalize_item_name
from ...core.units import normalize_default_unit
from ...schemas.backup import BackupTableResult
from ...schemas.common import OperationStatus
from ..storage_utils import normalize_storage_category

BACKUP_VERSION = "backup-v1"
BACKUP_RESTORE_RPC = "restore_device_backup_payload"
BACKUP_TABLES = [
    "inventory",
    "shopping_items",
    "favorite_recipes",
    "cooking_history",
    "notifications",
    "inventory_logs",
    "price_history",
]
CRITICAL_BACKUP_TABLES = {"inventory", "favorite_recipes"}
PASSTHROUGH_TABLES = ["shopping_items", "cooking_history", "notifications", "inventory_logs", "price_history"]
BACKUP_SELECT_COLUMNS = {
    "inventory": INVENTORY_SELECT_COLUMNS,
    "shopping_items": SHOPPING_ITEM_SELECT_COLUMNS,
    "favorite_recipes": FAVORITE_RECIPE_SELECT_COLUMNS,
    "cooking_history": COOKING_HISTORY_SELECT_COLUMNS,
    "notifications": NOTIFICATION_SELECT_COLUMNS,
    "inventory_logs": INVENTORY_LOG_SELECT_COLUMNS,
    "price_history": PRICE_HISTORY_SELECT_COLUMNS,
}


def safe_rows(payload: dict, table: str) -> list[dict]:
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get(table) if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def backup_status_from_warnings(warnings: list[str]) -> OperationStatus:
    return OperationStatus.DEGRADED if warnings else OperationStatus.OK


def validate_restore_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup restore payload must be a JSON object.",
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backup restore payload.data must be a JSON object.",
        )
    return payload


def inventory_upsert_rows(device_id: str, rows: list[dict]) -> list[dict]:
    upsert_rows: list[dict] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        name_normalized = normalize_item_name(name)
        if not name or not name_normalized:
            continue
        upsert_rows.append(
            {
                "device_id": device_id,
                "name": name,
                "name_normalized": name_normalized,
                "name_normalization_version": NAME_NORMALIZATION_VERSION,
                "quantity": row.get("quantity", 0),
                "unit": normalize_default_unit(row.get("unit")),
                "expiry_date": row.get("expiry_date"),
                "category": normalize_storage_category(row.get("category")),
                "image_url": row.get("image_url"),
            }
        )
    return upsert_rows


def favorite_recipe_rows(device_id: str, rows: list[dict]) -> list[dict]:
    upsert_rows: list[dict] = []
    for row in rows:
        recipe_id = str(row.get("recipe_id") or "").strip()
        if not recipe_id:
            continue
        upsert_rows.append(
            {
                "device_id": device_id,
                "recipe_id": recipe_id,
                "title": row.get("title"),
                "recipe_data": row.get("recipe_data") or {},
            }
        )
    return upsert_rows


def passthrough_rows(device_id: str, rows: list[dict]) -> list[dict]:
    insert_rows: list[dict] = []
    for row in rows:
        normalized = dict(row)
        normalized["device_id"] = device_id
        normalized.pop("id", None)
        if "unit" in normalized:
            normalized["unit"] = normalize_default_unit(normalized.get("unit"))
        insert_rows.append(normalized)
    return insert_rows


def shopping_item_rows(device_id: str, rows: list[dict]) -> list[dict]:
    insert_rows: list[dict] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        name_normalized = normalize_item_name(row.get("name_normalized") or name)
        if not name or not name_normalized:
            continue

        normalized = dict(row)
        normalized["device_id"] = device_id
        normalized["name"] = name
        normalized["name_normalized"] = name_normalized
        normalized["name_normalization_version"] = NAME_NORMALIZATION_VERSION
        normalized["unit"] = normalize_default_unit(normalized.get("unit"))
        normalized.pop("id", None)
        insert_rows.append(normalized)
    return insert_rows


def build_restore_payload(payload: dict, *, device_id: str) -> dict[str, list[dict]]:
    validated = validate_restore_payload(payload)
    return {
        "inventory": inventory_upsert_rows(device_id, safe_rows(validated, "inventory")),
        "shopping_items": shopping_item_rows(device_id, safe_rows(validated, "shopping_items")),
        "favorite_recipes": favorite_recipe_rows(device_id, safe_rows(validated, "favorite_recipes")),
        "cooking_history": passthrough_rows(device_id, safe_rows(validated, "cooking_history")),
        "notifications": passthrough_rows(device_id, safe_rows(validated, "notifications")),
        "inventory_logs": passthrough_rows(device_id, safe_rows(validated, "inventory_logs")),
        "price_history": passthrough_rows(device_id, safe_rows(validated, "price_history")),
    }


def parse_restore_counts(data: object) -> dict[str, int]:
    payload = data[0] if isinstance(data, list) and data else data
    if not isinstance(payload, dict):
        return {table: 0 for table in BACKUP_TABLES}

    counts: dict[str, int] = {}
    for table in BACKUP_TABLES:
        raw_value = payload.get(table)
        try:
            counts[table] = int(raw_value or 0)
        except (TypeError, ValueError):
            counts[table] = 0
    return counts


def ok_result(table: str, *, row_count: int) -> BackupTableResult:
    return BackupTableResult(
        table=table,
        status=OperationStatus.OK,
        row_count=row_count,
    )


def failed_result(table: str, *, error: str) -> BackupTableResult:
    return BackupTableResult(
        table=table,
        status=OperationStatus.FAILED,
        row_count=0,
        error=error,
    )
