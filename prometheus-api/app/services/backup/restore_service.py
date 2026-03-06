from __future__ import annotations

from fastapi import HTTPException, status
from supabase import Client

from ...schemas.backup import BackupRestoreRequest, BackupRestoreResponse
from .common import (
    BACKUP_SELECT_COLUMNS,
    BACKUP_TABLES,
    CRITICAL_BACKUP_TABLES,
    PASSTHROUGH_TABLES,
    backup_status_from_warnings,
    failed_result,
    favorite_recipe_rows,
    inventory_upsert_rows,
    ok_result,
    passthrough_rows,
    safe_rows,
)


def _snapshot_rows(db: Client, *, table: str, device_id: str) -> list[dict]:
    return (
        db.table(table)
        .select(BACKUP_SELECT_COLUMNS[table])
        .eq("device_id", device_id)
        .execute()
        .data
        or []
    )


def _restore_snapshot(db: Client, *, table: str, snapshot: list[dict]) -> None:
    if not snapshot:
        return
    if table == "inventory":
        db.table(table).upsert(snapshot, on_conflict="id").execute()
        return
    if table == "favorite_recipes":
        db.table(table).upsert(snapshot, on_conflict="device_id,recipe_id").execute()
        return
    db.table(table).insert(snapshot).execute()


def _replace_table(
    db: Client,
    *,
    table: str,
    device_id: str,
    rows: list[dict],
    write_rows,
) -> int:
    snapshot = _snapshot_rows(db, table=table, device_id=device_id)
    try:
        db.table(table).delete().eq("device_id", device_id).execute()
        if rows:
            write_rows(rows)
        return len(rows)
    except Exception:
        try:
            _restore_snapshot(db, table=table, snapshot=snapshot)
        except Exception:
            pass
        raise


def restore_backup(db: Client, *, device_id: str, payload: dict, mode: str) -> BackupRestoreResponse:
    restore_mode = (mode or "merge").strip().lower()
    if restore_mode not in {"merge", "replace"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be either merge or replace.")

    restored_counts: dict[str, int] = {table: 0 for table in BACKUP_TABLES}
    warnings: list[str] = []
    table_results = []
    critical_failures: list[str] = []

    inventory_rows = inventory_upsert_rows(device_id, safe_rows(payload, "inventory"))
    favorite_rows = favorite_recipe_rows(device_id, safe_rows(payload, "favorite_recipes"))
    passthrough_payloads = {
        table: passthrough_rows(device_id, safe_rows(payload, table))
        for table in PASSTHROUGH_TABLES
    }

    operations = [
        ("inventory", inventory_rows, lambda rows: db.table("inventory").upsert(rows, on_conflict="device_id,name_normalized").execute()),
        ("favorite_recipes", favorite_rows, lambda rows: db.table("favorite_recipes").upsert(rows, on_conflict="device_id,recipe_id").execute()),
    ]
    operations.extend(
        (
            table,
            passthrough_payloads[table],
            lambda rows, target_table=table: db.table(target_table).insert(rows).execute(),
        )
        for table in PASSTHROUGH_TABLES
    )

    for table, rows, writer in operations:
        try:
            if restore_mode == "replace":
                row_count = _replace_table(
                    db,
                    table=table,
                    device_id=device_id,
                    rows=rows,
                    write_rows=writer,
                )
            else:
                if rows:
                    writer(rows)
                row_count = len(rows)
            restored_counts[table] = row_count
            table_results.append(ok_result(table, row_count=row_count))
        except Exception as exc:
            warnings.append(f"backup restore failed table={table}")
            table_results.append(failed_result(table, error=str(exc)))
            if table in CRITICAL_BACKUP_TABLES:
                critical_failures.append(table)

    if critical_failures:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical backup restore tables failed: {', '.join(sorted(set(critical_failures)))}",
        )

    return BackupRestoreResponse(
        success=True,
        message="Backup restore completed.",
        status=backup_status_from_warnings(warnings),
        warnings=warnings,
        restored_counts=restored_counts,
        table_results=table_results,
    )


def restore_backup_payload(
    db: Client,
    *,
    device_id: str,
    request: BackupRestoreRequest,
) -> BackupRestoreResponse:
    return restore_backup(
        db,
        device_id=device_id,
        payload=request.payload,
        mode=request.mode,
    )
