from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from supabase import Client

IDEMPOTENCY_TABLE = "idempotency_keys"
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


def _is_missing_table_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "pgrst205" in text and IDEMPOTENCY_TABLE in text


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
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_idempotent_response(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str | None,
) -> JSONResponse | None:
    key = (idempotency_key or "").strip()
    if not key:
        return None

    try:
        rows = (
            db.table(IDEMPOTENCY_TABLE)
            .select("response_status,response_body,response_headers,expires_at")
            .eq("device_id", device_id)
            .eq("method", method.upper())
            .eq("path", path)
            .eq("idempotency_key", key)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise

    if not rows:
        return None

    row = rows[0]
    expires_at = _parse_timestamp(row.get("expires_at"))
    if expires_at and expires_at <= datetime.now(timezone.utc):
        try:
            (
                db.table(IDEMPOTENCY_TABLE)
                .delete()
                .eq("device_id", device_id)
                .eq("method", method.upper())
                .eq("path", path)
                .eq("idempotency_key", key)
                .execute()
            )
        except Exception:
            pass
        return None

    payload = row.get("response_body")
    if payload is None:
        payload = {}
    status_code = int(row.get("response_status") or 200)

    response_headers: dict[str, str] = {}
    raw_headers = row.get("response_headers")
    if isinstance(raw_headers, dict):
        for header_key, header_value in raw_headers.items():
            if header_key and header_value is not None:
                response_headers[str(header_key)] = str(header_value)
    response_headers["X-Idempotency-Replayed"] = "true"

    return JSONResponse(status_code=status_code, content=payload, headers=response_headers)


def save_idempotent_response(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str | None,
    status_code: int,
    payload: Any,
    headers: dict[str, str] | None = None,
) -> None:
    key = (idempotency_key or "").strip()
    if not key:
        return

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=IDEMPOTENCY_TTL_SECONDS)

    row = {
        "device_id": device_id,
        "method": method.upper(),
        "path": path,
        "idempotency_key": key,
        "response_status": int(status_code),
        "response_body": payload if payload is not None else {},
        "response_headers": headers or {},
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }

    try:
        db.table(IDEMPOTENCY_TABLE).upsert(
            [row],
            on_conflict="device_id,method,path,idempotency_key",
        ).execute()
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise
