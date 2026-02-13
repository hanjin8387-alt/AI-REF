from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import Client

from ..core.db_columns import (
    COOKING_HISTORY_SELECT_COLUMNS,
    FAVORITE_RECIPE_SELECT_COLUMNS,
    INVENTORY_SELECT_COLUMNS,
    RECIPE_SELECT_COLUMNS,
)
from ..core.config import get_settings
from ..core.database import get_db
from ..core.security import get_device_id, require_app_token
from ..schemas.schemas import (
    CookCompleteRequest,
    CookCompleteResponse,
    CookingHistoryItem,
    CookingHistoryResponse,
    FavoriteRecipeRequest,
    FavoriteToggleResponse,
    NotificationType,
    Recipe,
    RecipeListResponse,
)
from ..services.gemini_service import GeminiService, get_gemini_service
from ..services.notifications import create_notification
from ..services.recipe_cache import RecipeCacheProtocol, get_recipe_cache
from ..services.inventory_service import log_inventory_change
from ..services.recipe_helpers import (
    inventory_fingerprint,
    is_valid_uuid,
    load_favorite_ids,
    map_db_recipe,
    map_generated_recipe,
    parse_expiry_days,
    with_favorite_flags,
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
    dependencies=[Depends(require_app_token)],
)


def _load_recipe_from_sources(
    recipe_id: str,
    device_id: str,
    db: Client,
    recipe_cache: RecipeCacheProtocol,
) -> Recipe | None:
    recipe = recipe_cache.get(device_id, recipe_id)
    if recipe:
        return recipe

    if is_valid_uuid(recipe_id):
        recipe_row = db.table("recipes").select(RECIPE_SELECT_COLUMNS).eq("id", recipe_id).single().execute()
        if recipe_row.data:
            return map_db_recipe(recipe_row.data)

    favorite_row = (
        db.table("favorite_recipes")
        .select("recipe_data")
        .eq("device_id", device_id)
        .eq("recipe_id", recipe_id)
        .limit(1)
        .execute()
    )
    if favorite_row.data:
        recipe_data = favorite_row.data[0].get("recipe_data")
        if isinstance(recipe_data, dict):
            return Recipe(**recipe_data)

    return None


def _expiry_sort_key(row: dict) -> tuple[int, str]:
    expiry_raw = row.get("expiry_date")
    if expiry_raw is None:
        return (1, "")
    try:
        parsed = datetime.fromisoformat(str(expiry_raw).replace("Z", "")).date()
        return (0, parsed.isoformat())
    except ValueError:
        try:
            parsed = datetime.strptime(str(expiry_raw), "%Y-%m-%d").date()
            return (0, parsed.isoformat())
        except ValueError:
            return (1, str(expiry_raw))


def _find_best_inventory_match(inventory_rows: list[dict], ingredient_name: str) -> dict | None:
    needle = ingredient_name.strip().lower()
    if not needle:
        return None

    matched: list[dict] = []
    for row in inventory_rows:
        try:
            quantity = float(row.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0.0
        if quantity <= 0:
            continue

        row_name = str(row.get("name", "")).strip().lower()
        if not row_name:
            continue
        if needle in row_name or row_name in needle:
            matched.append(row)

    if not matched:
        return None

    matched.sort(key=_expiry_sort_key)
    return matched[0]


@router.get("/recommendations", response_model=RecipeListResponse)
@limiter.limit("20/minute")
async def get_recommendations(
    request: Request,
    limit: int = Query(5, ge=1, le=20, description="Number of recipes"),
    force_refresh: bool = Query(False, description="Bypass cache and call Gemini"),
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini_service),
    recipe_cache: RecipeCacheProtocol = Depends(get_recipe_cache),
):
    inventory_result = db.table("inventory").select(INVENTORY_SELECT_COLUMNS).eq("device_id", device_id).execute()
    inventory_rows = inventory_result.data or []
    if not inventory_rows:
        return RecipeListResponse(recipes=[], total_count=0)

    today = datetime.now().date()
    inventory_items: list[dict] = []
    for item in inventory_rows:
        inventory_items.append(
            {
                "name": item["name"],
                "quantity": float(item.get("quantity", 1)),
                "unit": item.get("unit", "unit"),
                "expiry_days": parse_expiry_days(item.get("expiry_date"), today),
            }
        )

    fingerprint = inventory_fingerprint(inventory_rows)
    if not force_refresh:
        cached = recipe_cache.get_batch(device_id, fingerprint, limit=limit)
        if cached is not None:
            favorite_ids = load_favorite_ids(db, device_id, [recipe.id for recipe in cached])
            recipes = with_favorite_flags(cached, favorite_ids)
            return RecipeListResponse(recipes=recipes, total_count=len(recipes))

    try:
        recipes_data = await gemini.generate_recipe_recommendations(inventory_items, max_recipes=limit)
    except Exception:
        logger.exception("recipe recommendation generation failed device_id=%s", device_id)
        recipes_data = []
    recipes = [map_generated_recipe(recipe_data, inventory_items) for recipe_data in recipes_data]
    recipes.sort(key=lambda recipe: recipe.priority_score, reverse=True)
    recipes = recipes[:limit]

    favorite_ids = load_favorite_ids(db, device_id, [recipe.id for recipe in recipes])
    recipes = with_favorite_flags(recipes, favorite_ids)

    recipe_cache.set_many(device_id, fingerprint, recipes, get_settings().recipe_cache_ttl_minutes)
    return RecipeListResponse(recipes=recipes, total_count=len(recipes))


@router.get("/favorites", response_model=RecipeListResponse)
async def get_favorite_recipes(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    result = (
        db.table("favorite_recipes")
        .select(FAVORITE_RECIPE_SELECT_COLUMNS, count="exact")
        .eq("device_id", device_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    rows = result.data or []
    recipes: list[Recipe] = []
    for row in rows:
        recipe_data = row.get("recipe_data")
        if not isinstance(recipe_data, dict):
            continue
        try:
            recipes.append(Recipe(**{**recipe_data, "is_favorite": True}))
        except Exception:
            continue

    return RecipeListResponse(recipes=recipes, total_count=int(result.count or len(recipes)))


@router.post("/{recipe_id}/favorite", response_model=FavoriteToggleResponse)
async def add_favorite_recipe(
    recipe_id: str,
    request: FavoriteRecipeRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    recipe_cache: RecipeCacheProtocol = Depends(get_recipe_cache),
):
    recipe: Recipe | None = None

    if request.recipe:
        if request.recipe.id != recipe_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipe ID does not match the request body.")
        recipe = request.recipe
    else:
        recipe = _load_recipe_from_sources(recipe_id, device_id, db, recipe_cache)

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe payload is required to save generated recommendations.",
        )

    db.table("favorite_recipes").upsert(
        {
            "device_id": device_id,
            "recipe_id": recipe_id,
            "recipe_data": recipe.model_dump(mode="json"),
            "title": recipe.title,
        },
        on_conflict="device_id,recipe_id",
    ).execute()

    return FavoriteToggleResponse(success=True, is_favorite=True, message="즐겨찾기에 추가했어요.")


@router.delete("/{recipe_id}/favorite", response_model=FavoriteToggleResponse)
async def remove_favorite_recipe(
    recipe_id: str,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    db.table("favorite_recipes").delete().eq("device_id", device_id).eq("recipe_id", recipe_id).execute()
    return FavoriteToggleResponse(success=True, is_favorite=False, message="즐겨찾기에서 제거했어요.")


@router.get("/history", response_model=CookingHistoryResponse)
async def get_cooking_history(
    limit: int = Query(20, ge=1, le=100, description="Rows per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    result = (
        db.table("cooking_history")
        .select(COOKING_HISTORY_SELECT_COLUMNS, count="exact")
        .eq("device_id", device_id)
        .order("cooked_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    rows = result.data or []
    items = [CookingHistoryItem(**row) for row in rows]
    total_count = int(result.count or len(items))
    has_more = offset + len(items) < total_count
    return CookingHistoryResponse(
        items=items,
        total_count=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/history/{history_id}", response_model=CookingHistoryItem)
async def get_cooking_history_detail(
    history_id: str,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    result = (
        db.table("cooking_history")
        .select(COOKING_HISTORY_SELECT_COLUMNS)
        .eq("id", history_id)
        .eq("device_id", device_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cooking history entry not found.")
    return CookingHistoryItem(**result.data)


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(
    recipe_id: str,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    recipe_cache: RecipeCacheProtocol = Depends(get_recipe_cache),
):
    recipe = _load_recipe_from_sources(recipe_id, device_id, db, recipe_cache)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")

    favorite_ids = load_favorite_ids(db, device_id, [recipe_id])
    return recipe.model_copy(update={"is_favorite": recipe_id in favorite_ids})


@router.post("/{recipe_id}/cook", response_model=CookCompleteResponse)
async def complete_cooking(
    recipe_id: str,
    request: CookCompleteRequest,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    recipe_cache: RecipeCacheProtocol = Depends(get_recipe_cache),
):
    if request.servings <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Servings must be at least 1.")

    recipe = _load_recipe_from_sources(recipe_id, device_id, db, recipe_cache)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")

    deducted_items: list[dict] = []
    base_servings = recipe.servings if recipe.servings > 0 else 1
    multiplier = request.servings / base_servings

    inventory_result = db.table("inventory").select(INVENTORY_SELECT_COLUMNS).eq("device_id", device_id).execute()
    working_inventory: list[dict] = [dict(row) for row in (inventory_result.data or [])]
    quantity_updates: dict[str, float] = {}
    deleted_ids: set[str] = set()

    for ingredient in recipe.ingredients:
        deduct_qty = max(0.0, ingredient.quantity * multiplier)
        if deduct_qty <= 0:
            continue

        inv_item = _find_best_inventory_match(working_inventory, ingredient.name)
        if not inv_item:
            continue

        inv_item_id = str(inv_item.get("id"))
        if not inv_item_id:
            continue

        current_qty = float(inv_item.get("quantity", 0))
        new_qty = max(0.0, current_qty - deduct_qty)

        if new_qty <= 0:
            inv_item["quantity"] = 0.0
            deleted_ids.add(inv_item_id)
            quantity_updates.pop(inv_item_id, None)
            deducted_items.append(
                {
                    "name": inv_item["name"],
                    "deducted": current_qty,
                    "remaining": 0,
                    "deleted": True,
                }
            )
        else:
            rounded_qty = round(new_qty, 2)
            inv_item["quantity"] = rounded_qty
            quantity_updates[inv_item_id] = rounded_qty
            deleted_ids.discard(inv_item_id)
            deducted_items.append(
                {
                    "name": inv_item["name"],
                    "deducted": round(deduct_qty, 2),
                    "remaining": rounded_qty,
                    "deleted": False,
                }
            )

    inventory_updates = [
        {"id": item_id, "quantity": new_qty}
        for item_id, new_qty in quantity_updates.items()
    ]
    recipe_uuid = recipe.id if is_valid_uuid(recipe.id) else None
    history_id = None
    try:
        rpc_result = db.rpc(
            "complete_cooking_transaction",
            {
                "p_device_id": device_id,
                "p_recipe_id": recipe_uuid,
                "p_recipe_title": recipe.title,
                "p_servings": request.servings,
                "p_deducted_items": deducted_items,
                "p_updates": inventory_updates,
                "p_delete_ids": list(deleted_ids),
            },
        ).execute()
        rpc_data = rpc_result.data
        if isinstance(rpc_data, list):
            first = rpc_data[0] if rpc_data else None
            if isinstance(first, dict):
                history_id = (
                    first.get("complete_cooking_transaction")
                    or first.get("history_id")
                    or first.get("result")
                )
            elif first is not None:
                history_id = str(first)
        elif isinstance(rpc_data, dict):
            history_id = (
                rpc_data.get("complete_cooking_transaction")
                or rpc_data.get("history_id")
                or rpc_data.get("result")
            )
        elif rpc_data is not None:
            history_id = str(rpc_data)

        if not history_id:
            raise RuntimeError("complete_cooking_transaction returned empty history id")
    except Exception as exc:
        logger.exception("complete cooking failed recipe_id=%s device_id=%s", recipe_id, device_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete cooking transaction.",
        ) from exc

    recipe_cache.invalidate_device(device_id)

    # Log inventory changes for statistics
    for item in deducted_items:
        log_inventory_change(
            db, device_id, item["name"], "cook",
            quantity_change=-item["deducted"],
            metadata={"recipe_title": recipe.title, "recipe_id": recipe.id},
        )

    create_notification(
        db=db,
        device_id=device_id,
        notification_type=NotificationType.COOKING,
        title="요리를 완료했어요",
        message=f"{recipe.title}를 {request.servings}인분 요리했어요.",
        metadata={"recipe_id": recipe.id, "history_id": history_id, "deducted_count": len(deducted_items)},
    )

    return CookCompleteResponse(
        success=True,
        message=f"요리를 완료했어요. 재료 {len(deducted_items)}개를 사용했어요.",
        deducted_items=deducted_items,
    )

