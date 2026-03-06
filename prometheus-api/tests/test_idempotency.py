from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.idempotency import load_idempotent_response, save_idempotent_response

from .fakes import FakeDB


def test_save_and_load_idempotent_response_round_trips_payload() -> None:
  db = FakeDB({'idempotency_keys': []})

  save_idempotent_response(
    db,
    device_id='device-1',
    method='POST',
    path='/inventory/bulk',
    idempotency_key='key-1',
    status_code=200,
    payload={'ok': True},
    headers={'X-Test': '1'},
  )

  replayed = load_idempotent_response(
    db,
    device_id='device-1',
    method='POST',
    path='/inventory/bulk',
    idempotency_key='key-1',
  )

  assert replayed is not None
  assert replayed.headers['x-idempotency-replayed'] == 'true'
  assert replayed.body == b'{"ok":true}'


def test_expired_idempotent_response_is_pruned() -> None:
  expired_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
  db = FakeDB(
    {
      'idempotency_keys': [
        {
          'device_id': 'device-1',
          'method': 'POST',
          'path': '/inventory/bulk',
          'idempotency_key': 'key-1',
          'response_status': 200,
          'response_body': {'ok': True},
          'response_headers': {},
          'expires_at': expired_at,
        }
      ]
    }
  )

  replayed = load_idempotent_response(
    db,
    device_id='device-1',
    method='POST',
    path='/inventory/bulk',
    idempotency_key='key-1',
  )

  assert replayed is None
  assert db.tables['idempotency_keys'] == []
