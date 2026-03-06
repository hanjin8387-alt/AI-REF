import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from supabase import Client

from ..core.db_columns import INVENTORY_SELECT_COLUMNS
from ..core.database import get_db
from ..core.idempotency import execute_idempotent_mutation
from ..core.normalization import NAME_NORMALIZATION_VERSION, normalize_item_name
from ..core.units import normalize_default_unit
from ..core.security import require_app_token, require_device_auth
from ..schemas.common import NotificationType
from ..schemas.inventory import (
    BulkInventoryRequest,
    BulkInventoryResponse,
    InventoryDeleteResponse,
    InventoryItem,
    InventoryListResponse,
    InventoryRestoreRequest,
    InventoryUpdateRequest,
)
from ..services.inventory_service import bulk_upsert_inventory, log_inventory_change
from ..services.notifications import create_notification
from ..services.storage_utils import normalize_storage_category

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_app_token)],
)




@router.get("", response_model=InventoryListResponse)
async def get_inventory(
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: str = Query("expiry_date", description="Sort key"),
    limit: int = Query(30, ge=1, le=200, description="Rows per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    updated_since: Optional[datetime] = Query(None, description="Return rows updated since this timestamp"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    query = db.table("inventory").select(INVENTORY_SELECT_COLUMNS, count="exact").eq("device_id", device_id)

    if category:
        query = query.eq("category", category)
    if updated_since is not None:
        query = query.gte("updated_at", updated_since.astimezone(timezone.utc).isoformat())

    if sort_by == "expiry_date":
        query = query.order("expiry_date", desc=False, nullsfirst=False)
    elif sort_by == "name":
        query = query.order("name", desc=False)
    elif sort_by == "created_at":
        query = query.order("created_at", desc=True)
    elif sort_by == "updated_at":
        query = query.order("updated_at", desc=True)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_by must be one of: expiry_date, name, created_at, updated_at.",
        )

    result = query.range(offset, offset + limit - 1).execute()
    rows = result.data or []
    total_count = int(result.count or 0)
    if total_count == 0 and rows:
        total_count = len(rows)

    items = [InventoryItem(**item) for item in rows]
    has_more = offset + len(items) < total_count
    return InventoryListResponse(
        items=items,
        total_count=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.post("/bulk", response_model=BulkInventoryResponse)
async def bulk_add_inventory(
    request_context: Request,
    request: BulkInventoryRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute() -> BulkInventoryResponse:
        if not request.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one item is required.",
            )

        raw_items = [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "expiry_date": item.expiry_date,
                "category": normalize_storage_category(item.category),
            }
            for item in request.items
        ]

        added_count, updated_count, items = bulk_upsert_inventory(db, device_id, raw_items)

        if added_count == 0 and updated_count == 0:
            return BulkInventoryResponse(success=True, added_count=0, updated_count=0, items=[])

        create_notification(
            db=db,
            device_id=device_id,
            notification_type=NotificationType.INVENTORY,
            title="재고가 업데이트되었어요",
            message=f"{added_count}개 추가, {updated_count}개 업데이트했어요.",
            metadata={"added_count": added_count, "updated_count": updated_count},
        )

        return BulkInventoryResponse(
            success=True,
            added_count=added_count,
            updated_count=updated_count,
            items=items,
        )

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_execute,
    )


@router.put("/{item_id}", response_model=InventoryItem)
async def update_inventory_item(
    request_context: Request,
    item_id: str,
    request: InventoryUpdateRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute() -> InventoryItem:
        existing = (
            db.table("inventory")
            .eq("id", item_id)
            .eq("device_id", device_id)
            .select(INVENTORY_SELECT_COLUMNS)
            .single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found.")

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
            updates["quantity"] = float(request.quantity)
        if request.unit is not None:
            updates["unit"] = normalize_default_unit(request.unit)
        if request.expiry_date is not None:
            updates["expiry_date"] = request.expiry_date.date().isoformat()
        if request.category is not None:
            updates["category"] = normalize_storage_category(request.category)

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

        try:
            updated = (
                db.table("inventory")
                .update(updates)
                .eq("id", item_id)
                .eq("device_id", device_id)
                .execute()
            )
        except Exception as exc:
            logger.exception("inventory update failed item_id=%s device_id=%s", item_id, device_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to update inventory item.") from exc

        if not updated.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update inventory item.")

        result = InventoryItem(**updated.data[0])
        old_qty = float(existing.data.get("quantity", 0))
        new_qty = float(result.quantity)
        if old_qty != new_qty:
            log_inventory_change(
                db, device_id, result.name, "update",
                quantity_change=round(new_qty - old_qty, 2),
                metadata={"item_id": item_id, "old_quantity": old_qty},
            )
        return result

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"item_id": item_id, **request.model_dump(mode="json", exclude_none=False)},
        handler=_execute,
    )


@router.delete("/{item_id}", response_model=InventoryDeleteResponse)
async def delete_inventory_item(
    request: Request,
    item_id: str,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute() -> InventoryDeleteResponse:
        existing_result = (
            db.table("inventory")
            .select(INVENTORY_SELECT_COLUMNS)
            .eq("id", item_id)
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )
        existing_rows = existing_result.data or []
        if not existing_rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found.")

        try:
            db.table("inventory").delete().eq("id", item_id).eq("device_id", device_id).execute()
        except Exception as exc:
            logger.exception("inventory delete failed item_id=%s device_id=%s", item_id, device_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to delete inventory item.") from exc

        deleted_item = InventoryItem(**existing_rows[0])

        log_inventory_change(
            db, device_id, deleted_item.name, "delete",
            quantity_change=-deleted_item.quantity,
            metadata={"item_id": item_id},
        )

        create_notification(
            db=db,
            device_id=device_id,
            notification_type=NotificationType.INVENTORY,
            title="재고 항목이 삭제되었어요",
            message=f"{deleted_item.name} 항목을 재고에서 삭제했어요.",
            metadata={"item_id": item_id, "name": deleted_item.name},
        )

        return InventoryDeleteResponse(
            success=True,
            message="재고 항목을 삭제했어요.",
            deleted_item=deleted_item,
        )

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request.method,
        path=request.url.path,
        idempotency_key=x_idempotency_key,
        request_payload={"item_id": item_id, "action": "delete"},
        handler=_execute,
    )


@router.post("/restore", response_model=InventoryItem)
async def restore_inventory_item(
    request_context: Request,
    request: InventoryRestoreRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    device_id: str = Depends(require_device_auth),
    db: Client = Depends(get_db),
):
    async def _execute() -> InventoryItem:
        name = request.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty.")
        normalized_name = normalize_item_name(name)

        existing = (
            db.table("inventory")
            .select(INVENTORY_SELECT_COLUMNS)
            .eq("device_id", device_id)
            .eq("name_normalized", normalized_name)
            .limit(1)
            .execute()
        )

        expiry_date = request.expiry_date.date().isoformat() if request.expiry_date else None
        normalized_category = normalize_storage_category(request.category)
        if existing.data:
            row = existing.data[0]
            updated = (
                db.table("inventory")
                .update(
                    {
                        "quantity": float(row.get("quantity", 0)) + max(float(request.quantity), 0.0),
                        "unit": normalize_default_unit(request.unit or row.get("unit")),
                        "expiry_date": expiry_date or row.get("expiry_date"),
                        "name_normalized": normalized_name,
                        "name_normalization_version": NAME_NORMALIZATION_VERSION,
                        "category": normalized_category if request.category is not None else row.get("category"),
                    }
                )
                .eq("id", row["id"])
                .eq("device_id", device_id)
                .execute()
            )
            if not updated.data:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore inventory item.")
            restored = InventoryItem(**updated.data[0])
        else:
            inserted = (
                db.table("inventory")
                .insert(
                    {
                        "device_id": device_id,
                        "name": name,
                        "name_normalized": normalized_name,
                        "name_normalization_version": NAME_NORMALIZATION_VERSION,
                        "quantity": max(float(request.quantity), 0.0),
                        "unit": normalize_default_unit(request.unit),
                        "expiry_date": expiry_date,
                        "category": normalized_category,
                    }
                )
                .execute()
            )
            if not inserted.data:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore inventory item.")
            restored = InventoryItem(**inserted.data[0])

        log_inventory_change(
            db, device_id, restored.name, "restore",
            quantity_change=float(request.quantity),
        )

        create_notification(
            db=db,
            device_id=device_id,
            notification_type=NotificationType.INVENTORY,
            title="재고 항목을 복구했어요",
            message=f"{restored.name} 항목을 복구했어요.",
            metadata={"item_id": restored.id, "name": restored.name},
        )

        return restored

    return await execute_idempotent_mutation(
        db,
        device_id=device_id,
        method=request_context.method,
        path=request_context.url.path,
        idempotency_key=x_idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_execute,
    )




