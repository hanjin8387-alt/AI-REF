from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .common import NotificationType


class NotificationItem(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    total_count: int
    unread_count: int
    limit: int
    offset: int
    has_more: bool


class MarkNotificationsReadRequest(BaseModel):
    ids: List[str] = Field(default_factory=list)


class MarkNotificationsReadResponse(BaseModel):
    success: bool
    updated_count: int
