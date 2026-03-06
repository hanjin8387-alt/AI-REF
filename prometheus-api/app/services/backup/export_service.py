from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from supabase import Client

from ...schemas.backup import BackupExportResponse
from .common import (
    BACKUP_SELECT_COLUMNS,
    BACKUP_TABLES,
    BACKUP_VERSION,
    CRITICAL_BACKUP_TABLES,
    backup_status_from_warnings,
    failed_result,
    ok_result,
)


def export_backup(db: Client, *, device_id: str) -> BackupExportResponse:
    data: dict[str, list[dict]] = {}
    warnings: list[str] = []
    table_results = []
    critical_failures: list[str] = []

    for table in BACKUP_TABLES:
        try:
            rows = (
                db.table(table)
                .select(BACKUP_SELECT_COLUMNS[table])
                .eq("device_id", device_id)
                .execute()
                .data
                or []
            )
            data[table] = rows
            table_results.append(ok_result(table, row_count=len(rows)))
        except Exception as exc:
            data[table] = []
            warnings.append(f"backup export failed table={table}")
            table_results.append(failed_result(table, error=str(exc)))
            if table in CRITICAL_BACKUP_TABLES:
                critical_failures.append(table)

    if critical_failures:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical backup export tables failed: {', '.join(critical_failures)}",
        )

    exported_at = datetime.now(timezone.utc)
    return BackupExportResponse(
        success=True,
        exported_at=exported_at,
        status=backup_status_from_warnings(warnings),
        warnings=warnings,
        table_results=table_results,
        payload={
            "version": BACKUP_VERSION,
            "device_id": device_id,
            "exported_at": exported_at.isoformat(),
            "data": data,
        },
    )


export_backup_payload = export_backup
