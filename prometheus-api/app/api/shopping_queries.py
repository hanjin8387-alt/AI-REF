from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from ..core.db_columns import SHOPPING_ITEM_SELECT_COLUMNS
from ..core.database import get_db
from ..core.security import require_device_auth
from ..schemas.schemas import LowStockSuggestionResponse, ShoppingItem, ShoppingItemStatus, ShoppingListResponse
from ..use_cases.shopping_use_cases import build_low_stock_suggestions
from .shopping_support import handle_shopping_table_error

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=ShoppingListResponse)
async def get_shopping_items(
    status_filter: Optional[ShoppingItemStatus] = Query(None, alias="status"),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    updated_since: Optional[datetime] = Query(None, description="Return rows updated since this timestamp"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    try:
        query = db.table("shopping_items").select(SHOPPING_ITEM_SELECT_COLUMNS, count="exact").eq("device_id", device_id)
        if status_filter is not None:
            query = query.eq("status", status_filter.value)
        if updated_since is not None:
            query = query.gte("updated_at", updated_since.astimezone(timezone.utc).isoformat())

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        rows = result.data or []
        items = [ShoppingItem(**row) for row in rows]
        total_count = int(result.count or len(items))
        has_more = offset + len(items) < total_count

        pending_count_result = (
            db.table("shopping_items")
            .select("id", count="exact")
            .eq("device_id", device_id)
            .eq("status", ShoppingItemStatus.PENDING.value)
            .limit(1)
            .execute()
        )
        purchased_count_result = (
            db.table("shopping_items")
            .select("id", count="exact")
            .eq("device_id", device_id)
            .eq("status", ShoppingItemStatus.PURCHASED.value)
            .limit(1)
            .execute()
        )

        pending_count = int(pending_count_result.count or 0)
        purchased_count = int(purchased_count_result.count or 0)

        return ShoppingListResponse(
            items=items,
            total_count=total_count,
            pending_count=pending_count,
            purchased_count=purchased_count,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )
    except HTTPException:
        raise
    except Exception as exc:
        handle_shopping_table_error(exc)
        logger.exception("shopping list load failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load shopping list.",
        ) from exc


@router.get("/suggestions/low-stock", response_model=LowStockSuggestionResponse)
async def get_low_stock_suggestions(
    lookback_days: int = Query(14, ge=3, le=60),
    threshold_days: int = Query(7, ge=1, le=30),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    try:
        inventory_rows = (
            db.table("inventory")
            .select("name,quantity,unit")
            .eq("device_id", device_id)
            .gt("quantity", 0)
            .execute()
            .data
            or []
        )
        consumption_rows = (
            db.table("inventory_logs")
            .select("item_name,action,quantity_change")
            .eq("device_id", device_id)
            .gte("created_at", (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat())
            .execute()
            .data
            or []
        )
        pending_rows = (
            db.table("shopping_items")
            .select("name")
            .eq("device_id", device_id)
            .eq("status", ShoppingItemStatus.PENDING.value)
            .execute()
            .data
            or []
        )

        suggestions = build_low_stock_suggestions(
            inventory_rows=inventory_rows,
            consumption_rows=consumption_rows,
            pending_shopping_rows=pending_rows,
            lookback_days=lookback_days,
            threshold_days=threshold_days,
        )
        return LowStockSuggestionResponse(items=suggestions, total_count=len(suggestions))
    except Exception as exc:
        handle_shopping_table_error(exc)
        logger.exception("low stock suggestion failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate low-stock suggestions.",
        ) from exc
