from __future__ import annotations

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
from ...schemas.schemas import BackupTableResult, OperationStatus
from ..storage_utils import normalize_storage_category

BACKUP_VERSION = "backup-v1"
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
