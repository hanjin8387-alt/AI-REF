from typing import Annotated
import secrets

from fastapi import Header, HTTPException, status

from .config import get_settings


def require_app_token(
    x_app_token: Annotated[str | None, Header(alias="X-App-Token")] = None,
) -> None:
    """Validate shared family app token."""
    settings = get_settings()

    if not settings.require_app_token:
        return

    if not settings.app_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server APP_TOKEN is not configured",
        )

    if not x_app_token or not secrets.compare_digest(x_app_token, settings.app_token):
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
