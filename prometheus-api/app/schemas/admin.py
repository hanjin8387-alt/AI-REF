from __future__ import annotations

from pydantic import BaseModel


class ExpiryCheckResponse(BaseModel):
    devices_checked: int = 0
    notifications_sent: int = 0
    errors: int = 0
