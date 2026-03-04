import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..core.config import get_settings
from ..core.database import get_db
from ..core.normalization import normalize_item_name
from ..core.security import (
    get_device_id,
    issue_device_token,
    require_app_token,
    require_device_auth,
)
from ..schemas.schemas import (
    BackupExportResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    BackupTableResult,
    BootstrapResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceTokenRevokeResponse,
    DeviceTokenRotateResponse,
    OperationStatus,
)
from ..services.storage_utils import normalize_storage_category

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
CRITICAL_BACKUP_TABLES = {"inventory", "favorite_recipes"}


def _safe_rows(payload: dict, table: str) -> list[dict]:
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get(table) if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _backup_status_from_warnings(warnings: list[str]) -> OperationStatus:
    return OperationStatus.DEGRADED if warnings else OperationStatus.OK


@router.get("/bootstrap", response_model=BootstrapResponse)
async def bootstrap(
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        device_rows = db.table("devices").select("device_id").eq("device_id", device_id).limit(1).execute().data or []
        settings = get_settings()
        return BootstrapResponse(
            api_ok=True,
            token_required=settings.require_app_token and settings.allow_legacy_app_token,
            app_id_required=True,
            device_registered=bool(device_rows),
            sync_pending_count=0,
            last_sync_at=None,
        )
    except Exception as exc:
        logger.exception("bootstrap check failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap check failed",
        ) from exc


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
        now = datetime.now(timezone.utc)
        settings = get_settings()
        token_ttl_hours = max(1, int(settings.device_token_ttl_hours))
        token_expires_at = now + timedelta(hours=token_ttl_hours)

        existing_rows = (
            db.table("devices")
            .select("token_version")
            .eq("device_id", request.device_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        current_version = int(existing_rows[0].get("token_version") or 0) if existing_rows else 0
        next_version = max(1, current_version + 1)

        device_token, device_secret_hash = issue_device_token()
        db.table("devices").upsert(
            {
                "device_id": request.device_id,
                "push_token": request.push_token,
                "platform": request.platform,
                "app_version": request.app_version,
                "device_secret_hash": device_secret_hash,
                "token_version": next_version,
                "token_expires_at": token_expires_at.isoformat(),
                "token_revoked_at": None,
                "last_used_at": now.isoformat(),
            },
            on_conflict="device_id",
        ).execute()
        return DeviceRegisterResponse(
            success=True,
            device_id=request.device_id,
            message="Device registered",
            device_token=device_token,
            token_version=next_version,
            token_expires_at=token_expires_at,
        )
    except Exception as exc:
        logger.exception("device registration failed device_id=%s", request.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from exc


@router.post("/device-token/rotate", response_model=DeviceTokenRotateResponse)
async def rotate_device_token(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    settings = get_settings()
    token_ttl_hours = max(1, int(settings.device_token_ttl_hours))
    token_expires_at = now + timedelta(hours=token_ttl_hours)

    rows = (
        db.table("devices")
        .select("token_version")
        .eq("device_id", device_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    current_version = int(rows[0].get("token_version") or 0)
    next_version = max(1, current_version + 1)
    device_token, device_secret_hash = issue_device_token()

    db.table("devices").update(
        {
            "device_secret_hash": device_secret_hash,
            "token_version": next_version,
            "token_expires_at": token_expires_at.isoformat(),
            "token_revoked_at": None,
            "last_used_at": now.isoformat(),
        }
    ).eq("device_id", device_id).execute()

    return DeviceTokenRotateResponse(
        success=True,
        device_id=device_id,
        device_token=device_token,
        token_version=next_version,
        token_expires_at=token_expires_at,
    )


@router.post("/device-token/revoke", response_model=DeviceTokenRevokeResponse)
async def revoke_device_token(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    revoked_at = datetime.now(timezone.utc).isoformat()
    db.table("devices").update(
        {
            "token_revoked_at": revoked_at,
        }
    ).eq("device_id", device_id).execute()
    return DeviceTokenRevokeResponse(
        success=True,
        device_id=device_id,
        message="Device token revoked",
    )


@router.get("/backup/export", response_model=BackupExportResponse)
async def export_backup(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    data: dict[str, list[dict]] = {}
    warnings: list[str] = []
    table_results: list[BackupTableResult] = []
    critical_failures: list[str] = []

    for table in BACKUP_TABLES:
        try:
            rows = db.table(table).select("*").eq("device_id", device_id).execute().data or []
            data[table] = rows
            table_results.append(
                BackupTableResult(
                    table=table,
                    status=OperationStatus.OK,
                    row_count=len(rows),
                )
            )
        except Exception as exc:
            error_message = str(exc)
            data[table] = []
            warnings.append(f"backup export failed table={table}")
            table_results.append(
                BackupTableResult(
                    table=table,
                    status=OperationStatus.FAILED,
                    row_count=0,
                    error=error_message,
                )
            )
            if table in CRITICAL_BACKUP_TABLES:
                critical_failures.append(table)

    if critical_failures:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical backup export tables failed: {', '.join(critical_failures)}",
        )

    payload = {
        "version": "backup-v1",
        "device_id": device_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    exported_at = datetime.now(timezone.utc)
    return BackupExportResponse(
        success=True,
        exported_at=exported_at,
        status=_backup_status_from_warnings(warnings),
        warnings=warnings,
        table_results=table_results,
        payload=payload,
    )


def _inventory_upsert_rows(device_id: str, rows: list[dict]) -> list[dict]:
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
                "quantity": row.get("quantity", 0),
                "unit": row.get("unit") or "개",
                "expiry_date": row.get("expiry_date"),
                "category": normalize_storage_category(row.get("category")),
            }
        )
    return upsert_rows


@router.post("/backup/restore", response_model=BackupRestoreResponse)
async def restore_backup(
    request: BackupRestoreRequest,
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    mode = (request.mode or "merge").strip().lower()
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be either merge or replace.")

    restored_counts: dict[str, int] = {table: 0 for table in BACKUP_TABLES}
    warnings: list[str] = []
    table_results: list[BackupTableResult] = []
    critical_failures: list[str] = []

    if mode == "replace":
        for table in BACKUP_TABLES:
            try:
                db.table(table).delete().eq("device_id", device_id).execute()
                table_results.append(
                    BackupTableResult(
                        table=table,
                        status=OperationStatus.OK,
                        row_count=0,
                    )
                )
            except Exception as exc:
                warnings.append(f"backup replace delete failed table={table}")
                table_results.append(
                    BackupTableResult(
                        table=table,
                        status=OperationStatus.FAILED,
                        row_count=0,
                        error=str(exc),
                    )
                )
                if table in CRITICAL_BACKUP_TABLES:
                    critical_failures.append(table)

    try:
        inventory_rows = _safe_rows(request.payload, "inventory")
        if inventory_rows:
            upsert_rows = _inventory_upsert_rows(device_id, inventory_rows)
            if upsert_rows:
                db.table("inventory").upsert(upsert_rows, on_conflict="device_id,name_normalized").execute()
            restored_counts["inventory"] = len(upsert_rows)
            table_results.append(
                BackupTableResult(
                    table="inventory",
                    status=OperationStatus.OK,
                    row_count=len(upsert_rows),
                )
            )

        favorite_rows = _safe_rows(request.payload, "favorite_recipes")
        if favorite_rows:
            upsert_rows = []
            for row in favorite_rows:
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
            if upsert_rows:
                db.table("favorite_recipes").upsert(upsert_rows, on_conflict="device_id,recipe_id").execute()
            restored_counts["favorite_recipes"] = len(upsert_rows)
            table_results.append(
                BackupTableResult(
                    table="favorite_recipes",
                    status=OperationStatus.OK,
                    row_count=len(upsert_rows),
                )
            )

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
                table_results.append(
                    BackupTableResult(
                        table=table,
                        status=OperationStatus.OK,
                        row_count=len(insert_rows),
                    )
                )
            except Exception as exc:
                warnings.append(f"backup restore insert failed table={table}")
                table_results.append(
                    BackupTableResult(
                        table=table,
                        status=OperationStatus.FAILED,
                        row_count=0,
                        error=str(exc),
                    )
                )
                if table in CRITICAL_BACKUP_TABLES:
                    critical_failures.append(table)

    except Exception as exc:
        logger.exception("backup restore failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore backup.",
        ) from exc

    if critical_failures:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical backup restore tables failed: {', '.join(sorted(set(critical_failures)))}",
        )

    return BackupRestoreResponse(
        success=True,
        message="Backup restore completed.",
        status=_backup_status_from_warnings(warnings),
        warnings=warnings,
        restored_counts=restored_counts,
        table_results=table_results,
    )
