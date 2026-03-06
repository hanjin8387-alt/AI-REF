"""Admin endpoints for scheduled tasks and migration observability."""
from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from supabase import Client

from ..core.config import get_settings
from ..core.database import get_db
from ..core.legacy_auth_observability import get_legacy_auth_event_counts
from ..core.idempotency import execute_idempotent_mutation
from ..schemas.common import NotificationType
from ..schemas.stats import ExpiryCheckResponse
from ..services.fcm_service import send_push_to_many
from ..services.notifications import create_notification

logger = logging.getLogger(__name__)
EXPIRY_PAGE_SIZE = 500

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def _chunked(values: list[str], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _fetch_expiring_inventory_rows(
    db: Client,
    *,
    today: date,
    threshold: date,
    page_size: int = EXPIRY_PAGE_SIZE,
) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        page_result = (
            db.table("inventory")
            .select("device_id, name, expiry_date, quantity")
            .lte("expiry_date", threshold.isoformat())
            .gte("expiry_date", today.isoformat())
            .gt("quantity", 0)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        page_rows = page_result.data or []
        rows.extend(page_rows)
        if len(page_rows) < page_size:
            break
        offset += page_size
    return rows


def _fetch_push_tokens(
    db: Client,
    *,
    device_ids: list[str],
    page_size: int = EXPIRY_PAGE_SIZE,
) -> dict[str, str]:
    push_tokens: dict[str, str] = {}
    if not device_ids:
        return push_tokens

    for chunk in _chunked(device_ids, page_size):
        devices_result = (
            db.table("devices")
            .select("device_id, push_token")
            .in_("device_id", chunk)
            .execute()
        )
        for row in devices_result.data or []:
            device_id = row.get("device_id")
            token = row.get("push_token")
            if device_id and token:
                push_tokens[str(device_id)] = str(token)

    return push_tokens


def _require_admin_token(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> None:
    settings = get_settings()
    token = settings.admin_token
    if not token or not secrets.compare_digest(x_admin_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


def _build_expiry_message(today: date, items: list[dict]) -> tuple[str, str]:
    d_day = [item for item in items if item.get("expiry_date") == today.isoformat()]
    d_1 = [item for item in items if item.get("expiry_date") == (today + timedelta(days=1)).isoformat()]

    item_names = [str(item["name"]) for item in items[:5]]
    names_text = ", ".join(item_names)
    if len(items) > 5:
        names_text += f" plus {len(items) - 5} more"

    if d_day:
        return "Items expire today", f"{names_text} expire today. Review inventory now."
    if d_1:
        return "Items expire tomorrow", f"{names_text} expire tomorrow."
    return "Items expiring soon", f"{names_text} expire within 3 days."


@router.post("/check-expiry", response_model=ExpiryCheckResponse)
async def check_expiring_items(
    request: Request,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    _: None = Depends(_require_admin_token),
    db: Client = Depends(get_db),
):
    async def _execute() -> ExpiryCheckResponse:
        today = datetime.now().date()
        threshold = today + timedelta(days=3)

        expiring_rows = _fetch_expiring_inventory_rows(
            db,
            today=today,
            threshold=threshold,
        )

        if not expiring_rows:
            return ExpiryCheckResponse(devices_checked=0, notifications_sent=0, errors=0)

        device_items: dict[str, list[dict]] = {}
        for row in expiring_rows:
            device_id = str(row.get("device_id") or "").strip()
            if device_id:
                device_items.setdefault(device_id, []).append(row)

        push_tokens = _fetch_push_tokens(db, device_ids=list(device_items.keys()))

        notifications_sent = 0
        errors = 0

        for device_id, items in device_items.items():
            try:
                title, message = _build_expiry_message(today, items)
                create_notification(
                    db=db,
                    device_id=device_id,
                    notification_type=NotificationType.EXPIRY,
                    title=title,
                    message=message,
                    metadata={
                        "expiring_count": len(items),
                        "item_names": [item["name"] for item in items],
                    },
                )

                push_token = push_tokens.get(device_id)
                if push_token:
                    send_push_to_many(
                        push_tokens=[push_token],
                        title=title,
                        body=message,
                        data={
                            "action": "open_inventory",
                            "expiring_count": str(len(items)),
                        },
                    )

                notifications_sent += 1
            except Exception:
                logger.exception("expiry check failed device_id=%s", device_id)
                errors += 1

        return ExpiryCheckResponse(
            devices_checked=len(device_items),
            notifications_sent=notifications_sent,
            errors=errors,
        )

    return await execute_idempotent_mutation(
        db,
        device_id="admin",
        method=request.method,
        path=request.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"action": "check-expiry"},
        handler=_execute,
    )


@router.get("/legacy-auth-metrics")
async def get_legacy_auth_metrics(
    _: None = Depends(_require_admin_token),
    db: Client = Depends(get_db),
):
    return {
        "legacy_auth_events": get_legacy_auth_event_counts(db=db),
    }
