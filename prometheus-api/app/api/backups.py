from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import Client

from ..core.database import get_db
from ..core.security import require_device_auth
from ..schemas.schemas import BackupExportResponse, BackupRestoreRequest, BackupRestoreResponse
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
    request: BackupRestoreRequest,
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return restore_backup(
        db,
        device_id=device_id,
        payload=request.payload,
        mode=request.mode,
    )
