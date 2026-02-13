from app.schemas.schemas import Recipe, RecipeIngredient
from app.services.recipe_cache import RecipeCache


def _recipe(recipe_id: str) -> Recipe:
    return Recipe(
        id=recipe_id,
        title=f"Recipe {recipe_id}",
        description="desc",
        cooking_time_minutes=10,
        difficulty="easy",
        servings=1,
        ingredients=[
            RecipeIngredient(
                name="egg",
                quantity=1,
                unit="ea",
                available=True,
                expiry_days=3,
            )
        ],
        instructions=["step 1"],
        priority_score=0.8,
    )


def test_recipe_cache_enforces_max_devices_limit() -> None:
    cache = RecipeCache(max_devices=2)

    cache.set_many("device-1", "fp-1", [_recipe("r1")], ttl_minutes=30)
    cache.set_many("device-2", "fp-2", [_recipe("r2")], ttl_minutes=30)
    cache.set_many("device-3", "fp-3", [_recipe("r3")], ttl_minutes=30)

    assert cache.get_batch("device-1", "fp-1") is None
    assert cache.get_batch("device-2", "fp-2") is not None
    assert cache.get_batch("device-3", "fp-3") is not None


def test_recipe_cache_falls_back_to_minimum_size_when_zero() -> None:
    cache = RecipeCache(max_devices=0)

    cache.set_many("device-1", "fp-1", [_recipe("r1")], ttl_minutes=30)
    cache.set_many("device-2", "fp-2", [_recipe("r2")], ttl_minutes=30)

    assert cache.get_batch("device-1", "fp-1") is None
    assert cache.get_batch("device-2", "fp-2") is not None
