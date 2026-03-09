"""Statistics dashboard API."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from supabase import Client

from ..core.db_columns import PRICE_HISTORY_SELECT_COLUMNS
from ..core.database import get_db
from ..core.security import require_app_token, require_device_auth
from ..schemas.inventory import PriceHistoryItem, PriceHistoryResponse
from ..schemas.stats import (
    CookingStats,
    InventoryStats,
    ShoppingStats,
    StatsSummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["statistics"],
    dependencies=[Depends(require_app_token)],
)


def _period_start(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "all":
        return None
    return now - timedelta(days=30)


def _is_missing_table_error(exc: Exception, table_name: str) -> bool:
    text = str(exc).lower()
    return "pgrst205" in text and table_name.lower() in text


@router.get("/summary", response_model=StatsSummaryResponse)
async def get_stats_summary(
    period: str = Query("month", description="week | month | all"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    start = _period_start(period)

    # --- Cooking stats ---
    cooking_rows: list[dict] = []
    total_cooked = 0
    try:
        cooking_query = (
            db.table("cooking_history")
            .select("id,recipe_title", count="exact")
            .eq("device_id", device_id)
        )
        if start:
            cooking_query = cooking_query.gte("cooked_at", start.isoformat())
        cooking_result = cooking_query.execute()
        cooking_rows = cooking_result.data or []
        total_cooked = int(cooking_result.count or len(cooking_rows))
    except Exception as exc:
        if _is_missing_table_error(exc, "cooking_history"):
            logger.warning("cooking_history table missing during stats query; returning zeroed cooking stats")
        else:
            raise

    recipe_counts: dict[str, int] = {}
    for row in cooking_rows:
        title = row.get("recipe_title", "")
        if title:
            recipe_counts[title] = recipe_counts.get(title, 0) + 1
    most_cooked = max(recipe_counts, key=recipe_counts.get, default=None) if recipe_counts else None

    days = 7 if period == "week" else (30 if period == "month" else max(1, len(cooking_rows)))
    avg_per_week = round(total_cooked / max(1, days / 7), 1) if total_cooked else 0.0

    cooking = CookingStats(
        total_cooked=total_cooked,
        most_cooked_recipe=most_cooked,
        average_per_week=avg_per_week,
    )

    # --- Inventory stats (from inventory_logs) ---
    log_rows: list[dict] = []
    try:
        logs_query = (
            db.table("inventory_logs")
            .select("action,item_name,quantity_change")
            .eq("device_id", device_id)
        )
        if start:
            logs_query = logs_query.gte("created_at", start.isoformat())
        logs_result = logs_query.execute()
        log_rows = logs_result.data or []
    except Exception as exc:
        if _is_missing_table_error(exc, "inventory_logs"):
            logger.warning("inventory_logs table missing during stats query; returning zeroed inventory log stats")
        else:
            raise

    total_added = sum(1 for r in log_rows if r.get("action") == "add")
    total_consumed = sum(1 for r in log_rows if r.get("action") == "cook")
    total_expired = sum(1 for r in log_rows if r.get("action") == "expire")
    total_actions = total_added + total_consumed + total_expired
    waste_rate = round(total_expired / max(1, total_actions), 3) if total_expired else 0.0

    ingredient_counts: dict[str, int] = {}
    for row in log_rows:
        if row.get("action") == "cook":
            name = row.get("item_name", "")
            if name:
                ingredient_counts[name] = ingredient_counts.get(name, 0) + 1
    most_used = max(ingredient_counts, key=ingredient_counts.get, default=None) if ingredient_counts else None

    cat_counts: dict[str, int] = {}
    try:
        inv_result = db.table("inventory").select("category").eq("device_id", device_id).execute()
        for row in (inv_result.data or []):
            cat = row.get("category") or "Uncategorized"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    except Exception as exc:
        if _is_missing_table_error(exc, "inventory"):
            logger.warning("inventory table missing during stats query; returning empty category breakdown")
        else:
            raise

    category_breakdown = [{"category": k, "count": v} for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])]

    inventory = InventoryStats(
        total_added=total_added,
        total_consumed=total_consumed,
        total_expired=total_expired,
        waste_rate=waste_rate,
        most_used_ingredient=most_used,
        category_breakdown=category_breakdown,
    )

    # --- Shopping stats ---
    total_items = 0
    total_purchased = 0
    try:
        shop_query = (
            db.table("shopping_items")
            .select("id,status", count="exact")
            .eq("device_id", device_id)
        )
        if start:
            shop_query = shop_query.gte("created_at", start.isoformat())
        shop_result = shop_query.execute()
        shop_rows = shop_result.data or []
        total_items = int(shop_result.count or len(shop_rows))
        total_purchased = sum(1 for r in shop_rows if r.get("status") == "purchased")
    except Exception as exc:
        if _is_missing_table_error(exc, "shopping_items"):
            logger.warning("shopping_items table missing during stats query; returning zeroed shopping stats")
        else:
            raise

    shopping = ShoppingStats(total_purchased=total_purchased, total_items=total_items)

    return StatsSummaryResponse(
        period=period,
        cooking=cooking,
        inventory=inventory,
        shopping=shopping,
    )


@router.get("/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    name: str | None = Query(None, description="Filter by item name"),
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        query = (
            db.table("price_history")
            .select(PRICE_HISTORY_SELECT_COLUMNS, count="exact")
            .eq("device_id", device_id)
            .gte("created_at", start.isoformat())
        )
        if name:
            query = query.ilike("item_name", f"%{name.strip()}%")
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        rows = result.data or []
        return PriceHistoryResponse(
            items=[PriceHistoryItem(**row) for row in rows],
            total_count=int(result.count or len(rows)),
        )
    except Exception as exc:
        if _is_missing_table_error(exc, "price_history"):
            logger.warning("price_history table missing during stats query; returning empty list")
            return PriceHistoryResponse(items=[], total_count=0)
        raise

