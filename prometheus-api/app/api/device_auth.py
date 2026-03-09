from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from supabase import Client

from ..core.database import get_db
from ..core.idempotency import execute_idempotent_mutation
from ..core.security import get_device_id, hash_device_token, require_device_auth
from ..schemas.auth import (
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
    request_context: Request,
    request: DeviceRegisterRequest,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    device_id: str = Depends(get_device_id),
    x_device_token: Annotated[str | None, Header(alias="X-Device-Token")] = None,
    db: Client = Depends(get_db),
):
    async def _execute(context) -> DeviceRegisterResponse:
        context.ensure_active()
        return register_device(
            db,
            request_device_id=request.device_id,
            header_device_id=device_id,
            current_device_token=x_device_token,
            push_token=request.push_token,
            platform=request.platform,
            app_version=request.app_version,
        )

    try:
        return await execute_idempotent_mutation(
            db,
            device_id=device_id,
            method=request_context.method,
            path=request_context.url.path,
            idempotency_key=x_idempotency_key,
            request_payload={
                **request.model_dump(mode="json"),
                "current_device_token_hash": hash_device_token(x_device_token) if x_device_token else None,
            },
            handler=_execute,
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
    request: Request,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request.method,
        path=request.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"device_id": device_id, "action": "rotate"},
        handler=lambda context: (context.ensure_active(), rotate_device_token(db, device_id=device_id))[1],
    )


@router.post("/device-token/revoke", response_model=DeviceTokenRevokeResponse)
async def revoke_device_token_route(
    request: Request,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request.method,
        path=request.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"device_id": device_id, "action": "revoke"},
        handler=lambda context: (context.ensure_active(), revoke_device_token(db, device_id=device_id))[1],
    )
