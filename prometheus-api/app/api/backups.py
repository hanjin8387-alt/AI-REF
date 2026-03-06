from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from supabase import Client

from ..core.database import get_db
from ..core.idempotency import execute_idempotent_mutation
from ..core.security import require_device_auth
from ..schemas.backup import BackupExportResponse, BackupRestoreRequest, BackupRestoreResponse
from ..services.backup import export_backup, restore_backup

router = APIRouter()


@router.get("/backup/export", response_model=BackupExportResponse)
async def export_backup_route(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return export_backup(db, device_id=device_id)


@router.post("/backup/restore", response_model=BackupRestoreResponse)
async def restore_backup_route(
    request_context: Request,
    request: BackupRestoreRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return await execute_idempotent_mutation(
        device_id=device_id,
        db=db,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        require_key=True,
        handler=lambda: restore_backup(
            db,
            device_id=device_id,
            payload=request.payload,
            mode=request.mode,
        ),
    )
