from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from uuid import UUID, uuid4

from supabase import Client

from ..core.units import normalize_default_unit
from ..schemas.schemas import Recipe, RecipeIngredient


def is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False


def parse_expiry_days(expiry_raw: str | None, today: date) -> int | None:
    if not expiry_raw:
        return None

    try:
        parsed = datetime.fromisoformat(expiry_raw.replace("Z", "")).date()
    except ValueError:
        try:
            parsed = datetime.strptime(expiry_raw, "%Y-%m-%d").date()
        except ValueError:
            return None

    return (parsed - today).days


def inventory_fingerprint(inventory_rows: list[dict]) -> str:
    normalized = []
    for row in inventory_rows:
        normalized.append(
            {
                "name": str(row.get("name", "")).strip().lower(),
                "quantity": round(float(row.get("quantity", 0) or 0), 2),
                "unit": normalize_default_unit(str(row.get("unit") or "")).lower(),
                "expiry_date": str(row.get("expiry_date") or ""),
            }
        )
    normalized.sort(key=lambda item: (item["name"], item["unit"], item["expiry_date"]))
    payload = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def map_generated_recipe(recipe_data: dict, inventory_items: list[dict]) -> Recipe:
    ingredients: list[RecipeIngredient] = []
    for ingredient_data in recipe_data.get("ingredients", []):
        ingredient_name = str(ingredient_data.get("name", "")).strip()
        if not ingredient_name:
            continue

        matched_inventory = next(
            (
                inventory_item
                for inventory_item in inventory_items
                if inventory_item["name"].lower() in ingredient_name.lower()
                or ingredient_name.lower() in inventory_item["name"].lower()
            ),
            None,
        )

        ingredients.append(
            RecipeIngredient(
                name=ingredient_name,
                quantity=float(ingredient_data.get("quantity", 1)),
                unit=normalize_default_unit(str(ingredient_data.get("unit") or "")),
                available=matched_inventory is not None,
                expiry_days=matched_inventory.get("expiry_days") if matched_inventory else None,
            )
        )

    return Recipe(
        id=str(recipe_data.get("id") or f"generated-{uuid4()}"),
        title=str(recipe_data.get("title") or "Recommended Recipe"),
        description=str(recipe_data.get("description") or ""),
        image_url=recipe_data.get("image_url"),
        cooking_time_minutes=int(recipe_data.get("cooking_time_minutes", 30)),
        difficulty=str(recipe_data.get("difficulty", "medium")),
        servings=int(recipe_data.get("servings", 2)),
        ingredients=ingredients,
        instructions=[str(step) for step in recipe_data.get("instructions", []) if str(step).strip()],
        priority_score=float(recipe_data.get("priority_score", 0.5)),
        recommendation_reason=str(recipe_data.get("recommendation_reason") or "").strip() or None,
        is_favorite=bool(recipe_data.get("is_favorite", False)),
    )


def map_db_recipe(recipe_data: dict) -> Recipe:
    ingredients_data = recipe_data.get("ingredients", [])
    if not isinstance(ingredients_data, list):
        ingredients_data = []
    ingredients = [RecipeIngredient(**ingredient) for ingredient in ingredients_data]

    instructions_data = recipe_data.get("instructions", [])
    if not isinstance(instructions_data, list):
        instructions_data = []

    return Recipe(
        id=str(recipe_data["id"]),
        title=str(recipe_data["title"]),
        description=str(recipe_data.get("description", "")),
        image_url=recipe_data.get("image_url"),
        cooking_time_minutes=int(recipe_data.get("cooking_time_minutes", 30)),
        difficulty=str(recipe_data.get("difficulty", "medium")),
        servings=int(recipe_data.get("servings", 2)),
        ingredients=ingredients,
        instructions=[str(step) for step in instructions_data if str(step).strip()],
        priority_score=float(recipe_data.get("priority_score", 0.0)),
        recommendation_reason=str(recipe_data.get("recommendation_reason") or "").strip() or None,
        is_favorite=bool(recipe_data.get("is_favorite", False)),
    )


def load_favorite_ids(db: Client, device_id: str, recipe_ids: list[str]) -> set[str]:
    if not recipe_ids:
        return set()

    try:
        result = (
            db.table("favorite_recipes")
            .select("recipe_id")
            .eq("device_id", device_id)
            .in_("recipe_id", recipe_ids)
            .execute()
        )
    except Exception:
        return set()

    return {str(row["recipe_id"]) for row in (result.data or [])}


def with_favorite_flags(recipes: list[Recipe], favorite_ids: set[str]) -> list[Recipe]:
    return [recipe.model_copy(update={"is_favorite": recipe.id in favorite_ids}) for recipe in recipes]
