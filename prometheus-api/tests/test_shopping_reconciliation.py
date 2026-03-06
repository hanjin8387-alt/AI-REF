from __future__ import annotations

from app.core.units import DEFAULT_UNIT
from app.services.shopping_reconciliation import plan_shopping_name_reconciliation


def test_shopping_reconciliation_backfills_runtime_canonical_name_and_unit() -> None:
  rows = [
    {
      "id": "shop-1",
      "device_id": "device-1",
      "name": "  Ｍilk  ",
      "name_normalized": "milk",
      "name_normalization_version": 1,
      "unit": "unit",
    },
    {
      "id": "shop-2",
      "device_id": "device-1",
      "name": "Eggs",
      "name_normalized": "eggs",
      "name_normalization_version": 2,
      "unit": DEFAULT_UNIT,
    },
  ]

  plan = plan_shopping_name_reconciliation(rows)

  assert plan.rows_seen == 2
  assert plan.rows_to_update == 1
  action = plan.actions[0]
  assert action.row_id == "shop-1"
  assert action.update_payload["name_normalized"] == "milk"
  assert action.update_payload["name_normalization_version"] == 2
  assert action.update_payload["unit"] == DEFAULT_UNIT
