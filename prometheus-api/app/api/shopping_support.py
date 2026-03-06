from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException, status

from ..services.notifications import create_notification

logger = logging.getLogger(__name__)

SHOPPING_TABLE_MISSING_DETAIL = "Shopping feature is not initialized. Please apply the latest schema.sql first."


def is_missing_shopping_table_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "pgrst205" in text and "shopping_items" in text


def handle_shopping_table_error(exc: Exception) -> None:
    if is_missing_shopping_table_error(exc):
        logger.error("shopping table missing: run schema.sql migration")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SHOPPING_TABLE_MISSING_DETAIL,
        ) from exc


def schedule_notification(**kwargs) -> None:
    async def _notify() -> None:
        try:
            await asyncio.to_thread(create_notification, **kwargs)
        except Exception:
            logger.exception("shopping notification dispatch failed")

    asyncio.create_task(_notify())
