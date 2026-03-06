from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import Client

from ..core.database import get_db
from ..core.security import get_device_id, require_device_auth
from ..schemas.schemas import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceTokenRevokeResponse,
    DeviceTokenRotateResponse,
)
from ..services.auth.device_tokens import register_device, revoke_device_token, rotate_device_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/device-register", response_model=DeviceRegisterResponse)
async def register_device_route(
    request: DeviceRegisterRequest,
    device_id: str = Depends(get_device_id),
    x_device_token: Annotated[str | None, Header(alias="X-Device-Token")] = None,
    db: Client = Depends(get_db),
):
    try:
        return register_device(
            db,
            request_device_id=request.device_id,
            header_device_id=device_id,
            current_device_token=x_device_token,
            push_token=request.push_token,
            platform=request.platform,
            app_version=request.app_version,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("device registration failed device_id=%s", request.device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from exc


@router.post("/device-token/rotate", response_model=DeviceTokenRotateResponse)
async def rotate_device_token_route(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return rotate_device_token(db, device_id=device_id)


@router.post("/device-token/revoke", response_model=DeviceTokenRevokeResponse)
async def revoke_device_token_route(
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return revoke_device_token(db, device_id=device_id)
