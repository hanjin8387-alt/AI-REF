from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    push_token: Optional[str] = Field(None, description="FCM push token")
    platform: str = Field(default="unknown", description="ios/android/web")
    app_version: Optional[str] = None


class DeviceRegisterResponse(BaseModel):
    success: bool
    device_id: str
    message: str
    device_token: str
    token_version: int = 1
    token_expires_at: datetime


class BootstrapResponse(BaseModel):
    api_ok: bool
    token_required: bool
    app_id_required: bool = True
    legacy_app_token_enabled: bool = False
    device_registered: bool
    sync_pending_count: int = 0
    last_sync_at: Optional[datetime] = None


class DeviceTokenRotateResponse(BaseModel):
    success: bool
    device_id: str
    device_token: str
    token_version: int
    token_expires_at: datetime


class DeviceTokenRevokeResponse(BaseModel):
    success: bool
    device_id: str
    message: str
