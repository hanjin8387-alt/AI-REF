from __future__ import annotations

from fastapi import HTTPException, status
from supabase import Client

from ...schemas.backup import BackupRestoreRequest, BackupRestoreResponse
from .common import (
    BACKUP_RESTORE_RPC,
    BACKUP_TABLES,
    backup_status_from_warnings,
    build_restore_payload,
    ok_result,
    parse_restore_counts,
)


def restore_backup(db: Client, *, device_id: str, payload: dict, mode: str) -> BackupRestoreResponse:
    restore_mode = (mode or "merge").strip().casefold()
    if restore_mode not in {"merge", "replace"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be either merge or replace.")

    prepared_payload = build_restore_payload(payload, device_id=device_id)

    try:
        rpc_result = db.rpc(
            BACKUP_RESTORE_RPC,
            {
                "p_device_id": device_id,
                "p_mode": restore_mode,
                "p_payload": prepared_payload,
            },
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore backup.",
        ) from exc

    restored_counts = parse_restore_counts(getattr(rpc_result, "data", None))
    table_results = [
        ok_result(table, row_count=restored_counts.get(table, 0))
        for table in BACKUP_TABLES
    ]
    return BackupRestoreResponse(
        success=True,
        message="Backup restore completed.",
        status=backup_status_from_warnings([]),
        warnings=[],
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
