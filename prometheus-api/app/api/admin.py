"""Admin endpoints for scheduled tasks (expiry checks, etc.)."""
import logging
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import Client

from ..core.config import get_settings
from ..core.database import get_db
from ..core.legacy_auth_observability import get_legacy_auth_event_counts
from ..schemas.schemas import ExpiryCheckResponse, NotificationType
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
                push_tokens[device_id] = token

    return push_tokens


def _require_admin_token(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> None:
    """Validate admin token for scheduled/admin endpoints."""
    settings = get_settings()
    token = settings.admin_token
    if not token or not secrets.compare_digest(x_admin_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


@router.post("/check-expiry", response_model=ExpiryCheckResponse)
async def check_expiring_items(
    _: None = Depends(_require_admin_token),
    db: Client = Depends(get_db),
):
    """Check all devices for expiring inventory and send push notifications.

    Designed to be called daily by Cloud Scheduler or cron.
    Checks items expiring within 3 days (D-3, D-1, D-day).
    """
    today = datetime.now().date()
    threshold = today + timedelta(days=3)

    expiring_rows = _fetch_expiring_inventory_rows(
        db,
        today=today,
        threshold=threshold,
    )

    if not expiring_rows:
        return ExpiryCheckResponse(devices_checked=0, notifications_sent=0, errors=0)

    # Group by device
    device_items: dict[str, list[dict]] = {}
    for row in expiring_rows:
        device_id = row.get("device_id", "")
        if device_id:
            device_items.setdefault(device_id, []).append(row)

    # Get push tokens for all affected devices
    device_ids = list(device_items.keys())
    push_tokens = _fetch_push_tokens(db, device_ids=device_ids)

    notifications_sent = 0
    errors = 0

    for device_id, items in device_items.items():
        try:
            # Categorize by urgency
            d_day = [i for i in items if i.get("expiry_date") == today.isoformat()]
            d_1 = [i for i in items if i.get("expiry_date") == (today + timedelta(days=1)).isoformat()]
            d_3 = [i for i in items if i not in d_day and i not in d_1]

            item_names = [i["name"] for i in items[:5]]
            names_text = ", ".join(item_names)
            if len(items) > 5:
                names_text += f" 외 {len(items) - 5}개"

            if d_day:
                title = "🚨 오늘 만료되는 재료!"
                message = f"{names_text}이(가) 오늘 만료됩니다. 빨리 사용하세요!"
            elif d_1:
                title = "⚠️ 내일 만료되는 재료"
                message = f"{names_text}이(가) 내일 만료됩니다."
            else:
                title = "🫑 유통기한 임박!"
                message = f"{names_text}이(가) 3일 내 만료됩니다."

            # Create in-app notification
            create_notification(
                db=db,
                device_id=device_id,
                notification_type=NotificationType.EXPIRY,
                title=title,
                message=message,
                metadata={
                    "expiring_count": len(items),
                    "d_day_count": len(d_day),
                    "item_names": [i["name"] for i in items],
                },
            )

            # Send push notification if token exists
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


@router.get("/legacy-auth-metrics")
async def get_legacy_auth_metrics(
    _: None = Depends(_require_admin_token),
):
    return {
        "legacy_auth_events": get_legacy_auth_event_counts(),
    }
