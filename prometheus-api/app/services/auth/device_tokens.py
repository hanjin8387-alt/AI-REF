from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from supabase import Client

from ...core.config import get_settings
from ...core.security import hash_device_token, issue_device_token
from ...schemas.auth import (
    BootstrapResponse,
    DeviceRegisterResponse,
    DeviceTokenRevokeResponse,
    DeviceTokenRotateResponse,
)


def _token_expiry() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    settings = get_settings()
    ttl_hours = max(1, int(settings.device_token_ttl_hours))
    return now, now + timedelta(hours=ttl_hours)


def _parse_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _requires_existing_token(row: dict[str, object], *, now: datetime) -> bool:
    expected_hash = str(row.get("device_secret_hash") or "").strip()
    if not expected_hash:
        return False

    revoked_at = _parse_timestamp(row.get("token_revoked_at"))
    if revoked_at is not None:
        return False

    expires_at = _parse_timestamp(row.get("token_expires_at"))
    if expires_at is not None and expires_at <= now:
        return False

    return True


def get_bootstrap_state(db: Client, *, device_id: str) -> BootstrapResponse:
    device_rows = db.table("devices").select("device_id").eq("device_id", device_id).limit(1).execute().data or []
    settings = get_settings()
    return BootstrapResponse(
        api_ok=True,
        token_required=settings.require_app_token and settings.allow_legacy_app_token,
        app_id_required=True,
        legacy_app_token_enabled=settings.allow_legacy_app_token,
        device_registered=bool(device_rows),
        sync_pending_count=0,
        last_sync_at=None,
    )


def register_device(
    db: Client,
    *,
    request_device_id: str,
    header_device_id: str,
    current_device_token: str | None,
    push_token: str | None,
    platform: str,
    app_version: str | None,
) -> DeviceRegisterResponse:
    if request_device_id != header_device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header/device id mismatch",
        )

    now, token_expires_at = _token_expiry()
    existing_rows = (
        db.table("devices")
        .select("device_secret_hash,token_expires_at,token_revoked_at,token_version")
        .eq("device_id", request_device_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing_rows and _requires_existing_token(existing_rows[0], now=now):
        if not current_device_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device already registered; provide the current device token to rotate it.",
            )

        provided_hash = hash_device_token(current_device_token)
        expected_hash = str(existing_rows[0].get("device_secret_hash") or "")
        if not secrets.compare_digest(provided_hash, expected_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid existing device token",
            )

    current_version = int(existing_rows[0].get("token_version") or 0) if existing_rows else 0
    next_version = max(1, current_version + 1)

    device_token, device_secret_hash = issue_device_token()
    db.table("devices").upsert(
        {
            "device_id": request_device_id,
            "push_token": push_token,
            "platform": platform,
            "app_version": app_version,
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
        device_id=request_device_id,
        message="Device registered",
        device_token=device_token,
        token_version=next_version,
        token_expires_at=token_expires_at,
    )


def rotate_device_token(db: Client, *, device_id: str) -> DeviceTokenRotateResponse:
    now, token_expires_at = _token_expiry()
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


def revoke_device_token(db: Client, *, device_id: str) -> DeviceTokenRevokeResponse:
    rows = (
        db.table("devices")
        .select("device_id")
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

    revoked_at = datetime.now(timezone.utc).isoformat()
    db.table("devices").update({"token_revoked_at": revoked_at}).eq("device_id", device_id).execute()
    return DeviceTokenRevokeResponse(
        success=True,
        device_id=device_id,
        message="Device token revoked",
    )


def register_device_token(
    db: Client,
    *,
    request_device_id: str,
    header_device_id: str,
    push_token: str | None,
    platform: str,
    app_version: str | None,
    current_device_token: str | None = None,
) -> DeviceRegisterResponse:
    return register_device(
        db,
        request_device_id=request_device_id,
        header_device_id=header_device_id,
        current_device_token=current_device_token,
        push_token=push_token,
        platform=platform,
        app_version=app_version,
    )
