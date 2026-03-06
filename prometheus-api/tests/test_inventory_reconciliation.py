from __future__ import annotations

from app.core.units import DEFAULT_UNIT
from app.services.inventory_reconciliation import plan_inventory_name_reconciliation


def test_reconciliation_merges_runtime_canonical_duplicates() -> None:
  rows = [
    {
      'id': 'a',
      'device_id': 'device-1',
      'name': ' Milk ',
      'name_normalized': 'milk',
      'name_normalization_version': 1,
      'quantity': 1,
      'unit': 'unit',
      'expiry_date': '2026-03-10',
      'category': '냉장',
      'created_at': '2026-03-01T00:00:00+00:00',
    },
    {
      'id': 'b',
      'device_id': 'device-1',
      'name': 'Ｍilk',
      'name_normalized': 'ｍilk',
      'name_normalization_version': 1,
      'quantity': 2,
      'unit': '',
      'expiry_date': '2026-03-08',
      'category': '냉장',
      'created_at': '2026-03-02T00:00:00+00:00',
    },
  ]

  plan = plan_inventory_name_reconciliation(rows)

  assert plan.rows_to_update == 1
  assert plan.rows_to_delete == 1
  action = plan.actions[0]
  assert action.keep_id == 'a'
  assert action.merge_ids == ['b']
  assert action.update_payload['name_normalized'] == 'milk'
  assert action.update_payload['quantity'] == 3
  assert action.update_payload['unit'] == DEFAULT_UNIT
  assert action.update_payload['expiry_date'] == '2026-03-08'
