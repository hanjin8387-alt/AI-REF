from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from supabase import Client

from .config import get_settings
from .database import get_db


def require_app_token(
    x_app_id: Annotated[str | None, Header(alias="X-App-ID")] = None,
    x_app_token: Annotated[str | None, Header(alias="X-App-Token")] = None,
) -> None:
    """Validate public app identity with optional legacy token compatibility."""
    settings = get_settings()

    if x_app_id:
        app_id = x_app_id.strip().lower()
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-App-ID header is required",
            )

        allowed_app_ids = settings.parsed_app_ids
        if allowed_app_ids and app_id not in allowed_app_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unknown app id",
            )
        return

    if not settings.allow_legacy_app_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-App-ID header is required",
        )

    if not x_app_token:
        if settings.require_app_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-App-ID or legacy X-App-Token header is required",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-App-ID header is required",
        )

    if not settings.app_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server legacy APP_TOKEN is not configured",
        )

    if not secrets.compare_digest(x_app_token, settings.app_token):
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


def _parse_timestamp(raw_value: object) -> datetime | None:
    if raw_value is None:
        return None

    if isinstance(raw_value, datetime):
        return raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)

    text = str(raw_value).strip()
    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


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
        .select("device_secret_hash,token_version,token_expires_at,token_revoked_at,last_used_at")
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

    now = datetime.now(timezone.utc)
    token_expires_at = _parse_timestamp(rows[0].get("token_expires_at"))
    if token_expires_at and token_expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token expired",
        )

    token_revoked_at = _parse_timestamp(rows[0].get("token_revoked_at"))
    if token_revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device token revoked",
        )

    try:
        db.table("devices").update({"last_used_at": now.isoformat()}).eq("device_id", device_id).execute()
    except Exception:
        # Best-effort observability field; auth should not fail if update fails.
        pass

    return device_id
