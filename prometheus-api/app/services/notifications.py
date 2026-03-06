from typing import Any
import logging

from supabase import Client

from ..schemas.common import NotificationType

logger = logging.getLogger(__name__)


def create_notification(
    db: Client,
    device_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "device_id": device_id,
        "type": notification_type.value,
        "title": title,
        "message": message,
        "metadata": metadata or {},
    }

    try:
        db.table("notifications").insert(payload).execute()
    except Exception:
        # Notifications are best-effort and must not break main flows.
        logger.warning(
            "notification insert failed device_id=%s type=%s",
            device_id,
            notification_type.value,
            exc_info=True,
        )
        return
