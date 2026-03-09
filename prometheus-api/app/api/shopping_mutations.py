from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from supabase import Client

from ..core.database import get_db
from ..core.idempotency import execute_idempotent_mutation
from ..core.normalization import NAME_NORMALIZATION_VERSION, normalize_item_name
from ..core.security import require_device_auth
from ..schemas.common import NotificationType
from ..schemas.inventory import InventoryItem
from ..schemas.shopping import (
    AddShoppingFromRecipeRequest,
    AddShoppingItemsRequest,
    AddShoppingItemsResponse,
    ShoppingCheckoutRequest,
    ShoppingCheckoutResponse,
    ShoppingDeleteResponse,
    ShoppingItem,
    ShoppingItemSource,
    ShoppingItemStatus,
    ShoppingItemUpdateRequest,
)
from ..services.notifications import create_notification
from ..use_cases.shopping_use_cases import (
    aggregate_shopping_items,
    apply_inventory_from_shopping,
    normalize_name,
    normalize_unit,
    upsert_pending_shopping_items,
)
from .shopping_queries import get_low_stock_suggestions
from .shopping_support import handle_shopping_table_error, schedule_notification

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/suggestions/low-stock/add", response_model=AddShoppingItemsResponse)
async def add_low_stock_suggestions(
    request_context: Request,
    lookback_days: int = Query(14, ge=3, le=60),
    threshold_days: int = Query(7, ge=1, le=30),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> AddShoppingItemsResponse:
        try:
            suggestion_response = await get_low_stock_suggestions(
                lookback_days=lookback_days,
                threshold_days=threshold_days,
                device_id=device_id,
                db=db,
            )
            aggregated = {
                normalize_name(item.name): {
                    "name": item.name,
                    "quantity": item.recommended_quantity,
                    "unit": item.unit,
                }
                for item in suggestion_response.items
                if item.name.strip()
            }
            if not aggregated:
                return AddShoppingItemsResponse(success=True, added_count=0, updated_count=0, items=[])

            context.ensure_active()
            added_count, updated_count, touched_rows = upsert_pending_shopping_items(
                db=db,
                device_id=device_id,
                aggregated=aggregated,
                source=ShoppingItemSource.LOW_STOCK,
                recipe_id=None,
                recipe_title=None,
            )

            if added_count or updated_count:
                context.ensure_active()
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
            handle_shopping_table_error(exc)
            logger.exception("add low stock suggestions failed device_id=%s", device_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add low-stock suggestions.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"lookback_days": lookback_days, "threshold_days": threshold_days},
        handler=_execute,
    )


@router.post("/items", response_model=AddShoppingItemsResponse)
async def add_shopping_items(
    request_context: Request,
    request: AddShoppingItemsRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> AddShoppingItemsResponse:
        try:
            if not request.items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one item is required.",
                )

            aggregated = aggregate_shopping_items(request.items)
            if not aggregated:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid item payload provided.",
                )

            context.ensure_active()
            added_count, updated_count, touched_rows = upsert_pending_shopping_items(
                db=db,
                device_id=device_id,
                aggregated=aggregated,
                source=request.source,
                recipe_id=request.recipe_id,
                recipe_title=request.recipe_title,
            )

            context.ensure_active()
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
            handle_shopping_table_error(exc)
            logger.exception("shopping add failed device_id=%s", device_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add shopping items.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_execute,
    )


@router.post("/from-recipe", response_model=AddShoppingItemsResponse)
async def add_shopping_from_recipe(
    request_context: Request,
    request: AddShoppingFromRecipeRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> AddShoppingItemsResponse:
        try:
            if not request.ingredients:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one ingredient is required.",
                )

            aggregated = aggregate_shopping_items(request.ingredients)
            if not aggregated:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid ingredient payload provided.",
                )

            context.ensure_active()
            added_count, updated_count, touched_rows = upsert_pending_shopping_items(
                db=db,
                device_id=device_id,
                aggregated=aggregated,
                source=ShoppingItemSource.RECIPE,
                recipe_id=request.recipe_id,
                recipe_title=request.recipe_title,
            )

            context.ensure_active()
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
            handle_shopping_table_error(exc)
            logger.exception("shopping add from recipe failed device_id=%s recipe_id=%s", device_id, request.recipe_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add recipe ingredients to shopping list.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_execute,
    )


@router.post("/checkout", response_model=ShoppingCheckoutResponse)
async def checkout_shopping_items(
    request_context: Request,
    request: ShoppingCheckoutRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> ShoppingCheckoutResponse:
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
                context.ensure_active()
                added_count, updated_count, inventory_items = apply_inventory_from_shopping(
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
                context.ensure_active()
                (
                    db.table("shopping_items")
                    .update(update_payload)
                    .eq("device_id", device_id)
                    .in_("id", checked_out_ids)
                    .execute()
                )

            if request.add_to_inventory:
                context.ensure_active()
                schedule_notification(
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
                context.ensure_active()
                schedule_notification(
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
            handle_shopping_table_error(exc)
            logger.exception("shopping checkout failed device_id=%s", device_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process shopping checkout.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_execute,
    )


@router.patch("/{item_id}", response_model=ShoppingItem)
async def update_shopping_item(
    request_context: Request,
    item_id: str,
    request: ShoppingItemUpdateRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> ShoppingItem:
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
                updates["name_normalized"] = normalize_item_name(name)
                updates["name_normalization_version"] = NAME_NORMALIZATION_VERSION
            if request.quantity is not None:
                if request.quantity < 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than or equal to 0.")
                updates["quantity"] = round(float(request.quantity), 2)
            if request.unit is not None:
                updates["unit"] = normalize_unit(request.unit)
            if request.status is not None:
                updates["status"] = request.status.value
                if request.status == ShoppingItemStatus.PURCHASED:
                    updates["purchased_at"] = datetime.now(timezone.utc).isoformat()
                elif request.status == ShoppingItemStatus.PENDING:
                    updates["purchased_at"] = None
                    updates["added_to_inventory"] = False

            if not updates:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

            context.ensure_active()
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
            handle_shopping_table_error(exc)
            logger.exception("shopping update failed item_id=%s device_id=%s", item_id, device_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to update shopping item.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"item_id": item_id, **request.model_dump(mode="json", exclude_none=False)},
        handler=_execute,
    )


@router.delete("/{item_id}", response_model=ShoppingDeleteResponse)
async def delete_shopping_item(
    request: Request,
    item_id: str,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute(context) -> ShoppingDeleteResponse:
        try:
            found_rows = (
                db.table("shopping_items")
                .select("id,device_id,name,name_normalized,name_normalization_version,quantity,unit,status,source,recipe_id,recipe_title,added_to_inventory,purchased_at,created_at,updated_at")
                .eq("id", item_id)
                .eq("device_id", device_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if not found_rows:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping item not found.")

            context.ensure_active()
            db.table("shopping_items").delete().eq("id", item_id).eq("device_id", device_id).execute()
            deleted_item = ShoppingItem(**found_rows[0])
            return ShoppingDeleteResponse(success=True, message="Deleted shopping item.", deleted_item=deleted_item)
        except HTTPException:
            raise
        except Exception as exc:
            handle_shopping_table_error(exc)
            logger.exception("shopping delete failed item_id=%s device_id=%s", item_id, device_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete shopping item.",
            ) from exc

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request.method,
        path=request.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"item_id": item_id, "action": "delete"},
        handler=_execute,
    )
