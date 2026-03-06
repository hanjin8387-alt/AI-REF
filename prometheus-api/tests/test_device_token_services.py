from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.auth.device_tokens import register_device, revoke_device_token, rotate_device_token

from .fakes import FakeDB


def test_rotate_device_token_increments_version_and_replaces_secret() -> None:
  db = FakeDB(
    {
      'devices': [
        {
          'device_id': 'device-12345678',
          'token_version': 2,
          'device_secret_hash': 'old',
        }
      ]
    }
  )

  rotated = rotate_device_token(db, device_id='device-12345678')

  assert rotated.token_version == 3
  assert rotated.device_token
  stored = db.tables['devices'][0]
  assert stored['token_version'] == 3
  assert stored['device_secret_hash'] != 'old'
  assert stored['token_revoked_at'] is None


def test_revoke_device_token_sets_revoked_timestamp() -> None:
  db = FakeDB({'devices': [{'device_id': 'device-12345678', 'token_version': 1}]})

  result = revoke_device_token(db, device_id='device-12345678')

  assert result.success is True
  assert db.tables['devices'][0]['token_revoked_at']


def test_register_device_token_upserts_existing_device() -> None:
  db = FakeDB({'devices': [{'device_id': 'device-12345678', 'token_version': 4}]})

  result = register_device(
    db,
    request_device_id='device-12345678',
    header_device_id='device-12345678',
    current_device_token=None,
    push_token='push-token',
    platform='ios',
    app_version='1.2.3',
  )

  assert result.token_version == 5
  stored = db.tables['devices'][0]
  assert stored['push_token'] == 'push-token'
  assert stored['platform'] == 'ios'
  assert stored['app_version'] == '1.2.3'


def test_rotate_device_token_missing_device_raises_not_found() -> None:
  db = FakeDB({'devices': []})

  with pytest.raises(HTTPException) as excinfo:
    rotate_device_token(db, device_id='missing-device')

  assert excinfo.value.status_code == 404


def test_register_device_requires_existing_token_for_active_device() -> None:
  db = FakeDB(
    {
      'devices': [
        {
          'device_id': 'device-12345678',
          'token_version': 4,
          'device_secret_hash': 'active-hash',
          'token_expires_at': '2999-01-01T00:00:00+00:00',
          'token_revoked_at': None,
        }
      ]
    }
  )

  with pytest.raises(HTTPException) as excinfo:
    register_device(
      db,
      request_device_id='device-12345678',
      header_device_id='device-12345678',
      current_device_token=None,
      push_token='push-token',
      platform='ios',
      app_version='1.2.3',
    )

  assert excinfo.value.status_code == 409
