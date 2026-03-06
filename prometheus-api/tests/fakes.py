from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass
class FakeResult:
  data: list[dict] | dict | None = None
  count: int | None = None


class FakeRPCQuery:
  def __init__(self, db: 'FakeDB', function_name: str, params: dict[str, Any]):
    self.db = db
    self.function_name = function_name
    self.params = params

  def execute(self):
    if self.function_name == 'increment_legacy_auth_event_counter':
      table = self.db.tables.setdefault('legacy_auth_event_counters', [])
      auth_mode = str(self.params.get('p_auth_mode') or '')
      outcome = str(self.params.get('p_outcome') or '')
      reason = str(self.params.get('p_reason') or '')

      existing = next(
        (
          row
          for row in table
          if row.get('auth_mode') == auth_mode and row.get('outcome') == outcome and row.get('reason') == reason
        ),
        None,
      )
      if existing is None:
        table.append(
          {
            'id': str(uuid4()),
            'auth_mode': auth_mode,
            'outcome': outcome,
            'reason': reason,
            'event_count': 1,
            'first_observed_at': '2026-01-01T00:00:00+00:00',
            'last_observed_at': '2026-01-01T00:00:00+00:00',
          }
        )
      else:
        existing['event_count'] = int(existing.get('event_count') or 0) + 1
        existing['last_observed_at'] = '2026-01-01T00:00:00+00:00'
      return FakeResult(data={'ok': True})

    raise AssertionError(f'Unsupported rpc: {self.function_name}')


class FakeTableQuery:
  def __init__(self, db: 'FakeDB', table_name: str):
    self.db = db
    self.table_name = table_name
    self._mode = 'select'
    self._filters: list[tuple[str, str, Any]] = []
    self._payload: Any = None
    self._single = False
    self._count_requested = False
    self._upsert_conflict: list[str] = []

  def _rows(self) -> list[dict]:
    return self.db.tables.setdefault(self.table_name, [])

  def select(self, _columns: str, count: str | None = None):
    self._mode = 'select'
    self._count_requested = count == 'exact'
    return self

  def eq(self, key: str, value: Any):
    self._filters.append(('eq', key, value))
    return self

  def in_(self, key: str, values: list[Any]):
    self._filters.append(('in', key, values))
    return self

  def limit(self, _value: int):
    return self

  def single(self):
    self._single = True
    return self

  def order(self, *_args, **_kwargs):
    return self

  def range(self, *_args, **_kwargs):
    return self

  def gt(self, key: str, value: Any):
    self._filters.append(('gt', key, value))
    return self

  def gte(self, key: str, value: Any):
    self._filters.append(('gte', key, value))
    return self

  def lte(self, key: str, value: Any):
    self._filters.append(('lte', key, value))
    return self

  def insert(self, payload: dict | list[dict]):
    self._mode = 'insert'
    self._payload = payload
    return self

  def upsert(self, payload: dict | list[dict], on_conflict: str):
    self._mode = 'upsert'
    self._payload = payload
    self._upsert_conflict = [item.strip() for item in on_conflict.split(',') if item.strip()]
    return self

  def update(self, payload: dict):
    self._mode = 'update'
    self._payload = payload
    return self

  def delete(self):
    self._mode = 'delete'
    self._payload = None
    return self

  def execute(self):
    rows = self._rows()
    matches = [row for row in rows if self._matches(row)]

    if self._mode == 'select':
      payload = deepcopy(matches[0]) if self._single else deepcopy(matches)
      count = len(matches) if self._count_requested else None
      return FakeResult(data=payload, count=count)

    if self._mode == 'insert':
      incoming = self._normalize_payload(self._payload)
      inserted = []
      for row in incoming:
        persisted = deepcopy(row)
        persisted.setdefault('id', str(uuid4()))
        rows.append(persisted)
        inserted.append(deepcopy(persisted))
      return FakeResult(data=inserted)

    if self._mode == 'upsert':
      incoming = self._normalize_payload(self._payload)
      upserted = []
      for row in incoming:
        persisted = deepcopy(row)
        if self._upsert_conflict:
          existing = self._find_conflict(rows, persisted)
          if existing is not None:
            existing.update(persisted)
            persisted = deepcopy(existing)
          else:
            persisted.setdefault('id', str(uuid4()))
            rows.append(persisted)
        else:
          persisted.setdefault('id', str(uuid4()))
          rows.append(persisted)
        upserted.append(deepcopy(persisted))
      return FakeResult(data=upserted)

    if self._mode == 'update':
      updated = []
      for row in matches:
        row.update(deepcopy(self._payload))
        updated.append(deepcopy(row))
      return FakeResult(data=updated)

    if self._mode == 'delete':
      deleted = [deepcopy(row) for row in matches]
      self.db.tables[self.table_name] = [row for row in rows if not self._matches(row)]
      return FakeResult(data=deleted)

    raise AssertionError(f'Unsupported mode: {self._mode}')

  def _normalize_payload(self, payload: dict | list[dict]) -> list[dict]:
    if isinstance(payload, list):
      return payload
    return [payload]

  def _find_conflict(self, rows: list[dict], candidate: dict) -> dict | None:
    for row in rows:
      if all(str(row.get(key)) == str(candidate.get(key)) for key in self._upsert_conflict):
        return row
    return None

  def _matches(self, row: dict) -> bool:
    for op, key, value in self._filters:
      current = row.get(key)
      if op == 'eq' and current != value:
        return False
      if op == 'in' and current not in value:
        return False
      if op == 'gt' and not (current > value):
        return False
      if op == 'gte' and not (current >= value):
        return False
      if op == 'lte' and not (current <= value):
        return False
    return True


class FakeDB:
  def __init__(self, tables: dict[str, list[dict]] | None = None):
    self.tables = deepcopy(tables or {})

  def table(self, table_name: str) -> FakeTableQuery:
    return FakeTableQuery(self, table_name)

  def rpc(self, function_name: str, params: dict[str, Any]) -> FakeRPCQuery:
    return FakeRPCQuery(self, function_name, params)
