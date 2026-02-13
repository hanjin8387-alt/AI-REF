from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from ..core.db_columns import SHOPPING_ITEM_SELECT_COLUMNS
from ..core.database import get_db
from ..core.security import get_device_id, require_app_token
from ..schemas.schemas import (
    AddShoppingFromRecipeRequest,
    AddShoppingItemsRequest,
    AddShoppingItemsResponse,
    InventoryItem,
    LowStockSuggestionItem,
    LowStockSuggestionResponse,
    NotificationType,
    ShoppingCheckoutRequest,
    ShoppingCheckoutResponse,
    ShoppingDeleteResponse,
    ShoppingItem,
    ShoppingItemInput,
    ShoppingItemSource,
    ShoppingItemStatus,
    ShoppingItemUpdateRequest,
    ShoppingListResponse,
)
from ..services.inventory_service import bulk_upsert_inventory
from ..services.notifications import create_notification

logger = logging.getLogger(__name__)

SHOPPING_TABLE_MISSING_DETAIL = ("Shopping feature is not initialized. Please apply the latest schema.sql first.")

router = APIRouter(
    prefix="/shopping",
    tags=["shopping"],
    dependencies=[Depends(require_app_token)],
)


def _is_missing_shopping_table_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "pgrst205" in text and "shopping_items" in text


def _handle_shopping_table_error(exc: Exception) -> None:
    if _is_missing_shopping_table_error(exc):
        logger.error("shopping table missing: run schema.sql migration")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=SHOPPING_TABLE_MISSING_DETAIL,
        ) from exc


def _normalize_name(value: str) -> str:
    return value.strip().lower()


def _normalize_unit(value: str | None) -> str:
    unit = (value or "").strip()
    if not unit:
        return "\uAC1C"
    if unit.lower() == "unit":
        return "\uAC1C"
    return unit


def _parse_quantity(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _aggregate_items(items: list[ShoppingItemInput]) -> dict[str, dict]:
    aggregated: dict[str, dict] = {}
    for item in items:
        name = item.name.strip()
        if not name:
            continue
        quantity = max(float(item.quantity), 0.0)
        if quantity <= 0:
            continue

        key = _normalize_name(name)
        payload = aggregated.setdefault(
            key,
            {
                "name": name,
                "quantity": 0.0,
                "unit": _normalize_unit(item.unit),
            },
        )
        payload["quantity"] += quantity
        if item.unit and item.unit.strip():
            payload["unit"] = _normalize_unit(item.unit)

    for payload in aggregated.values():
        payload["quantity"] = round(payload["quantity"], 2)
    return aggregated


def _upsert_pending_shopping_items(
    db: Client,
    device_id: str,
    aggregated: dict[str, dict],
    source: ShoppingItemSource,
    recipe_id: str | None,
    recipe_title: str | None,
) -> tuple[int, int, list[dict]]:
    existing_rows = (
        db.table("shopping_items")
        .select("id,name,quantity,unit")
        .eq("device_id", device_id)
        .eq("status", ShoppingItemStatus.PENDING.value)
        .execute()
        .data
        or []
    )
    existing_by_name = {str(row.get("name", "")).strip().lower(): row for row in existing_rows}

    added_count = 0
    updated_count = 0
    touched_rows: list[dict] = []

    for key, payload in aggregated.items():
        existing = existing_by_name.get(key)
        if existing:
            current_qty = _parse_quantity(existing.get("quantity"))
            new_quantity = round(current_qty + payload["quantity"], 2)
            updates: dict[str, object] = {
                "quantity": new_quantity,
                "unit": payload["unit"] or _normalize_unit(str(existing.get("unit") or "")),
            }
            if source != ShoppingItemSource.MANUAL:
                updates["source"] = source.value
            if recipe_id:
                updates["recipe_id"] = recipe_id
            if recipe_title:
                updates["recipe_title"] = recipe_title

            updated = (
                db.table("shopping_items")
                .update(updates)
                .eq("id", existing["id"])
                .eq("device_id", device_id)
                .execute()
            )
            if updated.data:
                touched_rows.append(updated.data[0])
                updated_count += 1
            continue

        inserted = (
            db.table("shopping_items")
            .insert(
                {
                    "device_id": device_id,
                    "name": payload["name"],
                    "quantity": payload["quantity"],
                    "unit": payload["unit"],
                    "status": ShoppingItemStatus.PENDING.value,
                    "source": source.value,
                    "recipe_id": recipe_id,
                    "recipe_title": recipe_title,
                    "added_to_inventory": False,
                }
            )
            .execute()
        )
        if inserted.data:
            touched_rows.append(inserted.data[0])
            added_count += 1

    return added_count, updated_count, touched_rows


def _apply_inventory_from_shopping(
    db: Client,
    device_id: str,
    shopping_rows: list[dict],
) -> tuple[int, int, list[InventoryItem]]:
    raw_items = []
    for row in shopping_rows:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        quantity = max(_parse_quantity(row.get("quantity")), 0.0)
        if quantity <= 0:
            continue
        raw_items.append(
            {
                "name": name,
                "quantity": quantity,
                "unit": _normalize_unit(str(row.get("unit") or "")),
            }
        )

    return bulk_upsert_inventory(db, device_id, raw_items)


def _build_low_stock_suggestions(
    inventory_rows: list[dict],
    consumption_rows: list[dict],
    pending_shopping_rows: list[dict],
    lookback_days: int,
    threshold_days: int,
) -> list[LowStockSuggestionItem]:
    pending_names = {str(row.get("name", "")).strip().lower() for row in pending_shopping_rows}

    daily_usage_by_name: dict[str, float] = {}
    for row in consumption_rows:
        if str(row.get("action", "")).lower() != "cook":
            continue
        item_name = str(row.get("item_name", "")).strip().lower()
        if not item_name:
            continue
        qty = abs(_parse_quantity(row.get("quantity_change")))
        if qty <= 0:
            continue
        daily_usage_by_name[item_name] = daily_usage_by_name.get(item_name, 0.0) + (qty / max(1, lookback_days))

    suggestions: list[LowStockSuggestionItem] = []
    for row in inventory_rows:
        item_name_raw = str(row.get("name", "")).strip()
        item_name = item_name_raw.lower()
        if not item_name or item_name in pending_names:
            continue

        current_qty = max(_parse_quantity(row.get("quantity")), 0.0)
        if current_qty <= 0:
            continue

        daily_usage = daily_usage_by_name.get(item_name, 0.0)
        if daily_usage <= 0:
            continue

        predicted_days = round(current_qty / daily_usage, 1)
        if predicted_days > threshold_days:
            continue

        recommended_qty = max(round((daily_usage * 7) - current_qty, 2), 1.0)
        suggestions.append(
            LowStockSuggestionItem(
                name=item_name_raw,
                current_quantity=round(current_qty, 2),
                unit=_normalize_unit(str(row.get("unit") or "")),
                predicted_days_left=predicted_days,
                recommended_quantity=recommended_qty,
            )
        )

    suggestions.sort(key=lambda item: item.predicted_days_left)
    return suggestions


@router.get("", response_model=ShoppingListResponse)
async def get_shopping_items(
    status_filter: Optional[ShoppingItemStatus] = Query(None, alias="status"),
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        query = db.table("shopping_items").select(SHOPPING_ITEM_SELECT_COLUMNS, count="exact").eq("device_id", device_id)
        if status_filter is not None:
            query = query.eq("status", status_filter.value)

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
        _handle_shopping_table_error(exc)
        logger.exception("shopping list load failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load shopping list.",
        ) from exc


@router.get("/suggestions/low-stock", response_model=LowStockSuggestionResponse)
async def get_low_stock_suggestions(
    lookback_days: int = Query(14, ge=3, le=60),
    threshold_days: int = Query(7, ge=1, le=30),
    device_id: str = Depends(get_device_id),
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

        suggestions = _build_low_stock_suggestions(
            inventory_rows=inventory_rows,
            consumption_rows=consumption_rows,
            pending_shopping_rows=pending_rows,
            lookback_days=lookback_days,
            threshold_days=threshold_days,
        )
        return LowStockSuggestionResponse(items=suggestions, total_count=len(suggestions))
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("low stock suggestion failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate low-stock suggestions.",
        ) from exc


@router.post("/suggestions/low-stock/add", response_model=AddShoppingItemsResponse)
async def add_low_stock_suggestions(
    lookback_days: int = Query(14, ge=3, le=60),
    threshold_days: int = Query(7, ge=1, le=30),
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        suggestion_response = await get_low_stock_suggestions(
            lookback_days=lookback_days,
            threshold_days=threshold_days,
            device_id=device_id,
            db=db,
        )
        aggregated = {
            item.name.strip().lower(): {
                "name": item.name,
                "quantity": item.recommended_quantity,
                "unit": item.unit,
            }
            for item in suggestion_response.items
            if item.name.strip()
        }
        if not aggregated:
            return AddShoppingItemsResponse(success=True, added_count=0, updated_count=0, items=[])

        added_count, updated_count, touched_rows = _upsert_pending_shopping_items(
            db=db,
            device_id=device_id,
            aggregated=aggregated,
            source=ShoppingItemSource.LOW_STOCK,
            recipe_id=None,
            recipe_title=None,
        )

        if added_count or updated_count:
            create_notification(
                db=db,
                device_id=device_id,
                notification_type=NotificationType.SYSTEM,
                title="Added low-stock suggestions",
                message=f"Added {added_count} item(s), updated {updated_count} item(s).",
                metadata={"added_count": added_count, "updated_count": updated_count},
            )

        return AddShoppingItemsResponse(
            success=True,
            added_count=added_count,
            updated_count=updated_count,
            items=[ShoppingItem(**row) for row in touched_rows],
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("add low stock suggestions failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add low-stock suggestions.",
        ) from exc


@router.post("/items", response_model=AddShoppingItemsResponse)
async def add_shopping_items(
    request: AddShoppingItemsRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        if not request.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one item is required.",
            )

        aggregated = _aggregate_items(request.items)
        if not aggregated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid item payload provided.",
            )

        added_count, updated_count, touched_rows = _upsert_pending_shopping_items(
            db=db,
            device_id=device_id,
            aggregated=aggregated,
            source=request.source,
            recipe_id=request.recipe_id,
            recipe_title=request.recipe_title,
        )

        create_notification(
            db=db,
            device_id=device_id,
            notification_type=NotificationType.SYSTEM,
            title="Shopping list updated",
            message=f"Added {added_count} item(s), updated {updated_count} item(s).",
            metadata={"added_count": added_count, "updated_count": updated_count},
        )

        return AddShoppingItemsResponse(
            success=True,
            added_count=added_count,
            updated_count=updated_count,
            items=[ShoppingItem(**row) for row in touched_rows],
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("shopping add failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add shopping items.",
        ) from exc


@router.post("/from-recipe", response_model=AddShoppingItemsResponse)
async def add_shopping_from_recipe(
    request: AddShoppingFromRecipeRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        if not request.ingredients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one ingredient is required.",
            )

        aggregated = _aggregate_items(request.ingredients)
        if not aggregated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid ingredient payload provided.",
            )

        added_count, updated_count, touched_rows = _upsert_pending_shopping_items(
            db=db,
            device_id=device_id,
            aggregated=aggregated,
            source=ShoppingItemSource.RECIPE,
            recipe_id=request.recipe_id,
            recipe_title=request.recipe_title,
        )

        create_notification(
            db=db,
            device_id=device_id,
            notification_type=NotificationType.SYSTEM,
            title="Added recipe ingredients to shopping list",
            message=f"{request.recipe_title}: applied {added_count + updated_count} item(s).",
            metadata={"recipe_id": request.recipe_id, "count": added_count + updated_count},
        )

        return AddShoppingItemsResponse(
            success=True,
            added_count=added_count,
            updated_count=updated_count,
            items=[ShoppingItem(**row) for row in touched_rows],
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("shopping add from recipe failed device_id=%s recipe_id=%s", device_id, request.recipe_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add recipe ingredients to shopping list.",
        ) from exc


@router.post("/checkout", response_model=ShoppingCheckoutResponse)
async def checkout_shopping_items(
    request: ShoppingCheckoutRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        query = (
            db.table("shopping_items")
            .select("id,name,quantity,unit")
            .eq("device_id", device_id)
            .eq("status", ShoppingItemStatus.PENDING.value)
        )
        if request.ids:
            query = query.in_("id", request.ids)
        pending_rows = query.execute().data or []

        if not pending_rows:
            return ShoppingCheckoutResponse(
                success=True,
                checked_out_count=0,
                added_count=0,
                updated_count=0,
                inventory_items=[],
            )

        added_count = 0
        updated_count = 0
        inventory_items: list[InventoryItem] = []

        if request.add_to_inventory:
            added_count, updated_count, inventory_items = _apply_inventory_from_shopping(
                db=db,
                device_id=device_id,
                shopping_rows=pending_rows,
            )

        checked_out_ids = [str(row["id"]) for row in pending_rows if row.get("id")]
        if checked_out_ids:
            update_payload = {
                "status": ShoppingItemStatus.PURCHASED.value,
                "purchased_at": datetime.now(timezone.utc).isoformat(),
                "added_to_inventory": bool(request.add_to_inventory),
            }
            (
                db.table("shopping_items")
                .update(update_payload)
                .eq("device_id", device_id)
                .in_("id", checked_out_ids)
                .execute()
            )

        if request.add_to_inventory:
            create_notification(
                db=db,
                device_id=device_id,
                notification_type=NotificationType.INVENTORY,
                title="Shopping checkout completed",
                message=f"Inventory updated: added {added_count}, updated {updated_count}.",
                metadata={
                    "checked_out_count": len(checked_out_ids),
                    "added_count": added_count,
                    "updated_count": updated_count,
                },
            )
        else:
            create_notification(
                db=db,
                device_id=device_id,
                notification_type=NotificationType.SYSTEM,
                title="Marked shopping items as purchased",
                message=f"Marked {len(checked_out_ids)} item(s) as purchased.",
                metadata={"checked_out_count": len(checked_out_ids)},
            )

        return ShoppingCheckoutResponse(
            success=True,
            checked_out_count=len(checked_out_ids),
            added_count=added_count,
            updated_count=updated_count,
            inventory_items=inventory_items,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("shopping checkout failed device_id=%s", device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process shopping checkout.",
        ) from exc


@router.patch("/{item_id}", response_model=ShoppingItem)
async def update_shopping_item(
    item_id: str,
    request: ShoppingItemUpdateRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        found_rows = (
            db.table("shopping_items")
            .select("id")
            .eq("id", item_id)
            .eq("device_id", device_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not found_rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping item not found.")

        updates: dict[str, object] = {}
        if request.name is not None:
            name = request.name.strip()
            if not name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty.")
            updates["name"] = name
        if request.quantity is not None:
            if request.quantity < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than or equal to 0.")
            updates["quantity"] = round(float(request.quantity), 2)
        if request.unit is not None:
            updates["unit"] = _normalize_unit(request.unit)
        if request.status is not None:
            updates["status"] = request.status.value
            if request.status == ShoppingItemStatus.PURCHASED:
                updates["purchased_at"] = datetime.now(timezone.utc).isoformat()
            elif request.status == ShoppingItemStatus.PENDING:
                updates["purchased_at"] = None
                updates["added_to_inventory"] = False

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

        updated = (
            db.table("shopping_items")
            .update(updates)
            .eq("id", item_id)
            .eq("device_id", device_id)
            .execute()
        )
        if not updated.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update shopping item.")
        return ShoppingItem(**updated.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("shopping update failed item_id=%s device_id=%s", item_id, device_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to update shopping item.",
        ) from exc


@router.delete("/{item_id}", response_model=ShoppingDeleteResponse)
async def delete_shopping_item(
    item_id: str,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    try:
        found_rows = (
            db.table("shopping_items")
            .select(SHOPPING_ITEM_SELECT_COLUMNS)
            .eq("id", item_id)
            .eq("device_id", device_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not found_rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping item not found.")

        db.table("shopping_items").delete().eq("id", item_id).eq("device_id", device_id).execute()
        deleted_item = ShoppingItem(**found_rows[0])
        return ShoppingDeleteResponse(success=True, message="Deleted shopping item.", deleted_item=deleted_item)
    except HTTPException:
        raise
    except Exception as exc:
        _handle_shopping_table_error(exc)
        logger.exception("shopping delete failed item_id=%s device_id=%s", item_id, device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete shopping item.",
        ) from exc

