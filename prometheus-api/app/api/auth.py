import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..core.db_columns import (
    COOKING_HISTORY_SELECT_COLUMNS,
    FAVORITE_RECIPE_SELECT_COLUMNS,
    INVENTORY_LOG_SELECT_COLUMNS,
    INVENTORY_SELECT_COLUMNS,
    NOTIFICATION_SELECT_COLUMNS,
    PRICE_HISTORY_SELECT_COLUMNS,
    SHOPPING_ITEM_SELECT_COLUMNS,
)
from ..core.database import get_db
from ..core.security import get_device_id, require_app_token
from ..schemas.schemas import (
    BackupExportResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(require_app_token)],
)

BACKUP_TABLES = [
    "inventory",
    "shopping_items",
    "favorite_recipes",
    "cooking_history",
    "notifications",
    "inventory_logs",
    "price_history",
]

BACKUP_SELECT_COLUMNS: dict[str, str] = {
    "inventory": INVENTORY_SELECT_COLUMNS,
    "shopping_items": SHOPPING_ITEM_SELECT_COLUMNS,
    "favorite_recipes": FAVORITE_RECIPE_SELECT_COLUMNS,
    "cooking_history": COOKING_HISTORY_SELECT_COLUMNS,
    "notifications": NOTIFICATION_SELECT_COLUMNS,
    "inventory_logs": INVENTORY_LOG_SELECT_COLUMNS,
    "price_history": PRICE_HISTORY_SELECT_COLUMNS,
}


@router.post("/device-register", response_model=DeviceRegisterResponse)
async def register_device(
    request: DeviceRegisterRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    if request.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header/device id mismatch",
        )

    try:
        db.table("devices").upsert(
            {
                "device_id": request.device_id,
                "push_token": request.push_token,
                "platform": request.platform,
                "app_version": request.app_version,
            },
            on_conflict="device_id",
        ).execute()
        return DeviceRegisterResponse(
            success=True,
            device_id=request.device_id,
            message="Device registered",
        )
    except Exception as exc:
        logger.exception("device registration failed device_id=%s", request.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from exc


@router.get("/backup/export", response_model=BackupExportResponse)
async def export_backup(
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    data: dict[str, list[dict]] = {}
    try:
        for table in BACKUP_TABLES:
            try:
                select_columns = BACKUP_SELECT_COLUMNS.get(table, "id")
                rows = db.table(table).select(select_columns).eq("device_id", device_id).execute().data or []
                data[table] = rows
            except Exception:
                logger.warning("backup export skipped table=%s (missing or query error)", table, exc_info=True)
                data[table] = []

        payload = {
            "version": "backup-v1",
            "device_id": device_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        return BackupExportResponse(success=True, exported_at=datetime.now(timezone.utc), payload=payload)
    except Exception as exc:
        logger.exception("backup export failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="백업 내보내기에 실패했습니다.",
        ) from exc


def _safe_rows(payload: dict, table: str) -> list[dict]:
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get(table) if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


@router.post("/backup/restore", response_model=BackupRestoreResponse)
async def restore_backup(
    request: BackupRestoreRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    mode = (request.mode or "merge").strip().lower()
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode는 merge 또는 replace만 허용됩니다.")

    restored_counts: dict[str, int] = {table: 0 for table in BACKUP_TABLES}

    try:
        if mode == "replace":
            for table in BACKUP_TABLES:
                try:
                    db.table(table).delete().eq("device_id", device_id).execute()
                except Exception:
                    logger.warning("backup replace delete skipped table=%s", table, exc_info=True)

        inventory_rows = _safe_rows(request.payload, "inventory")
        if inventory_rows:
            upsert_rows = []
            for row in inventory_rows:
                upsert_rows.append(
                    {
                        "device_id": device_id,
                        "name": row.get("name"),
                        "quantity": row.get("quantity", 0),
                        "unit": row.get("unit") or "개",
                        "expiry_date": row.get("expiry_date"),
                        "category": row.get("category"),
                    }
                )
            if upsert_rows:
                db.table("inventory").upsert(upsert_rows, on_conflict="device_id,name").execute()
                restored_counts["inventory"] = len(upsert_rows)

        favorite_rows = _safe_rows(request.payload, "favorite_recipes")
        if favorite_rows:
            upsert_rows = []
            for row in favorite_rows:
                upsert_rows.append(
                    {
                        "device_id": device_id,
                        "recipe_id": row.get("recipe_id"),
                        "title": row.get("title"),
                        "recipe_data": row.get("recipe_data") or {},
                    }
                )
            db.table("favorite_recipes").upsert(upsert_rows, on_conflict="device_id,recipe_id").execute()
            restored_counts["favorite_recipes"] = len(upsert_rows)

        passthrough_tables = ["shopping_items", "cooking_history", "notifications", "inventory_logs", "price_history"]
        for table in passthrough_tables:
            rows = _safe_rows(request.payload, table)
            if not rows:
                continue

            insert_rows = []
            for row in rows:
                normalized = dict(row)
                normalized["device_id"] = device_id
                normalized.pop("id", None)
                insert_rows.append(normalized)

            if not insert_rows:
                continue
            try:
                db.table(table).insert(insert_rows).execute()
                restored_counts[table] = len(insert_rows)
            except Exception:
                logger.warning("backup restore insert skipped table=%s", table, exc_info=True)

        return BackupRestoreResponse(
            success=True,
            message="백업 복원을 완료했어요.",
            restored_counts=restored_counts,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("backup restore failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="백업 복원에 실패했습니다.",
        ) from exc
