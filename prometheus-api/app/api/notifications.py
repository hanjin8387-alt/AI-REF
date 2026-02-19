from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..core.db_columns import NOTIFICATION_SELECT_COLUMNS
from ..core.database import get_db
from ..core.security import require_app_token, require_device_auth
from ..schemas.schemas import (
    MarkNotificationsReadRequest,
    MarkNotificationsReadResponse,
    NotificationItem,
    NotificationListResponse,
)

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_app_token)],
)


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    only_unread: bool = Query(False),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    query = db.table("notifications").select(NOTIFICATION_SELECT_COLUMNS, count="exact").eq("device_id", device_id)
    if only_unread:
        query = query.eq("is_read", False)

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    rows = result.data or []
    items = [NotificationItem(**row) for row in rows]
    total_count = int(result.count or len(items))
    has_more = offset + len(items) < total_count

    unread_result = (
        db.table("notifications")
        .select("id", count="exact")
        .eq("device_id", device_id)
        .eq("is_read", False)
        .limit(1)
        .execute()
    )
    unread_count = int(unread_result.count or 0)

    return NotificationListResponse(
        items=items,
        total_count=total_count,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/read", response_model=MarkNotificationsReadResponse)
async def mark_notifications_read(
    request: MarkNotificationsReadRequest,
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    payload = {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}
    query = db.table("notifications").update(payload).eq("device_id", device_id).eq("is_read", False)

    if request.ids:
        query = query.in_("id", request.ids)

    result = query.execute()
    updated_count = len(result.data or [])
    return MarkNotificationsReadResponse(success=True, updated_count=updated_count)
