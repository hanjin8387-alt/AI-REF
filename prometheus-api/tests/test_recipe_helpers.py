from __future__ import annotations

from app.services.recipe_helpers import inventory_fingerprint, map_generated_recipe


def test_recipe_helpers_use_runtime_canonical_name_matching() -> None:
  inventory_items = [
    {"name": "Ｍilk", "quantity": 1, "unit": "개", "expiry_days": 2},
    {"name": "Straße Bread", "quantity": 1, "unit": "개", "expiry_days": 4},
  ]

  recipe = map_generated_recipe(
    {
      "id": "generated-1",
      "title": "Breakfast",
      "description": "desc",
      "ingredients": [
        {"name": "milk", "quantity": 1, "unit": "unit"},
        {"name": "STRASSE bread", "quantity": 1, "unit": "unit"},
      ],
      "instructions": ["mix"],
    },
    inventory_items,
  )

  assert [ingredient.available for ingredient in recipe.ingredients] == [True, True]
  assert inventory_fingerprint(inventory_items) == inventory_fingerprint(
    [{"name": "milk", "quantity": 1, "unit": "unit", "expiry_days": 2}, {"name": "strasse bread", "quantity": 1, "unit": "개", "expiry_days": 4}]
  )
