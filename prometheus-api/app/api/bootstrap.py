from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from ..core.database import get_db
from ..core.security import get_device_id
from ..schemas.auth import BootstrapResponse
from ..services.auth.device_tokens import get_bootstrap_state

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/bootstrap", response_model=BootstrapResponse)
async def bootstrap(
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        return get_bootstrap_state(db, device_id=device_id)
    except Exception as exc:
        logger.exception("bootstrap check failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap check failed",
        ) from exc
