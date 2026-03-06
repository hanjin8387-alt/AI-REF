from __future__ import annotations

from app.core.normalization import NAME_NORMALIZATION_VERSION
from app.core.units import DEFAULT_UNIT
from app.services.backup.export_service import export_backup
from app.services.backup.restore_service import restore_backup

from .fakes import FakeDB


def test_export_backup_returns_only_device_scoped_rows() -> None:
  db = FakeDB(
    {
      'inventory': [
        {'id': '1', 'device_id': 'device-a', 'name': 'Milk'},
        {'id': '2', 'device_id': 'device-b', 'name': 'Eggs'},
      ],
      'shopping_items': [],
      'favorite_recipes': [],
      'cooking_history': [],
      'notifications': [],
      'inventory_logs': [],
      'price_history': [],
    }
  )

  result = export_backup(db, device_id='device-a')

  assert result.success is True
  assert result.payload['data']['inventory'] == [{'id': '1', 'device_id': 'device-a', 'name': 'Milk'}]
  assert result.status.value == 'ok'


def test_restore_backup_normalizes_inventory_and_units() -> None:
  db = FakeDB(
    {
      'inventory': [],
      'shopping_items': [],
      'favorite_recipes': [],
      'cooking_history': [],
      'notifications': [],
      'inventory_logs': [],
      'price_history': [],
    }
  )
  payload = {
    'data': {
      'inventory': [{'name': '  Milk  ', 'quantity': 2, 'unit': 'unit', 'category': '냉장'}],
      'shopping_items': [{'name': 'Eggs', 'quantity': 3, 'unit': ''}],
      'favorite_recipes': [{'recipe_id': 'recipe-1', 'title': 'Soup', 'recipe_data': {'ok': True}}],
    }
  }

  result = restore_backup(
    db,
    device_id='device-a',
    payload=payload,
    mode='merge',
  )

  assert result.success is True
  inventory_row = db.tables['inventory'][0]
  assert inventory_row['name_normalized'] == 'milk'
  assert inventory_row['name_normalization_version'] == NAME_NORMALIZATION_VERSION
  assert inventory_row['unit'] == DEFAULT_UNIT
  assert db.tables['shopping_items'][0]['unit'] == DEFAULT_UNIT
  assert db.tables['favorite_recipes'][0]['recipe_id'] == 'recipe-1'
