from __future__ import annotations

import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from .config import get_settings
from .database import get_db


def require_app_token(
    x_app_token: Annotated[str | None, Header(alias="X-App-Token")] = None,
) -> None:
    """Validate shared family app token."""
    settings = get_settings()

    if not settings.require_app_token:
        return

    if not settings.app_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server APP_TOKEN is not configured",
        )

    if not x_app_token or not secrets.compare_digest(x_app_token, settings.app_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid app token",
        )


def get_device_id(
    x_device_id: Annotated[str | None, Header(alias="X-Device-ID")] = None,
) -> str:
    """Require and validate stable device id header."""
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID header is required",
        )

    device_id = x_device_id.strip()
    if len(device_id) < 8 or len(device_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID must be 8-128 characters",
        )

    allowed_device_ids = get_settings().parsed_allowed_device_ids
    if allowed_device_ids and device_id not in allowed_device_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device is not allowed",
        )

    return device_id


def hash_device_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_device_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(40)
    return raw_token, hash_device_token(raw_token)


def require_device_auth(
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    x_device_token: Annotated[str | None, Header(alias="X-Device-Token")] = None,
) -> str:
    if not x_device_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Device-Token header is required",
        )

    rows = (
        db.table("devices")
        .select("device_secret_hash")
        .eq("device_id", device_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unknown device",
        )

    expected_hash = str(rows[0].get("device_secret_hash") or "")
    actual_hash = hash_device_token(x_device_token)
    if not expected_hash or not secrets.compare_digest(expected_hash, actual_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid device token",
        )

    return device_id
