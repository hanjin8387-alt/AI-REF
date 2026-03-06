from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class FakeResult:
    data: list[dict] | dict | bool | None = None
    count: int | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class FakeRPCQuery:
    def __init__(self, db: "FakeDB", function_name: str, params: dict[str, Any]):
        self.db = db
        self.function_name = function_name
        self.params = params

    def execute(self):
        return self.db.execute_rpc(self.function_name, self.params)


class FakeTableQuery:
    def __init__(self, db: "FakeDB", table_name: str):
        self.db = db
        self.table_name = table_name
        self._mode = "select"
        self._filters: list[tuple[str, str, Any]] = []
        self._payload: Any = None
        self._single = False
        self._count_requested = False
        self._upsert_conflict: list[str] = []
        self._order_key: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None

    def _rows(self) -> list[dict]:
        return self.db.tables.setdefault(self.table_name, [])

    def select(self, _columns: str, count: str | None = None):
        self._mode = "select"
        self._count_requested = count == "exact"
        return self

    def eq(self, key: str, value: Any):
        self._filters.append(("eq", key, value))
        return self

    def in_(self, key: str, values: list[Any]):
        self._filters.append(("in", key, values))
        return self

    def limit(self, value: int):
        self._range = (0, max(0, value - 1))
        return self

    def single(self):
        self._single = True
        return self

    def order(self, key: str, desc: bool = False, **_kwargs):
        self._order_key = key
        self._order_desc = desc
        return self

    def range(self, start: int, end: int):
        self._range = (start, end)
        return self

    def gt(self, key: str, value: Any):
        self._filters.append(("gt", key, value))
        return self

    def gte(self, key: str, value: Any):
        self._filters.append(("gte", key, value))
        return self

    def lt(self, key: str, value: Any):
        self._filters.append(("lt", key, value))
        return self

    def lte(self, key: str, value: Any):
        self._filters.append(("lte", key, value))
        return self

    def ilike(self, key: str, pattern: str):
        self._filters.append(("ilike", key, pattern))
        return self

    def insert(self, payload: dict | list[dict]):
        self._mode = "insert"
        self._payload = payload
        return self

    def upsert(self, payload: dict | list[dict], on_conflict: str):
        self._mode = "upsert"
        self._payload = payload
        self._upsert_conflict = [item.strip() for item in on_conflict.split(",") if item.strip()]
        return self

    def update(self, payload: dict):
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        self._payload = None
        return self

    def execute(self):
        with self.db._lock:
            if self.table_name in self.db.table_failures:
                raise RuntimeError(f"Table failure injected: {self.table_name}")

            rows = self._rows()
            matches = [row for row in rows if self._matches(row)]
            matches = self._apply_order(matches)
            count = len(matches) if self._count_requested else None
            matches = self._apply_range(matches)

            if self._mode == "select":
                payload = deepcopy(matches[0]) if self._single and matches else (None if self._single else deepcopy(matches))
                return FakeResult(data=payload, count=count)

            if self._mode == "insert":
                incoming = self._normalize_payload(self._payload)
                inserted = []
                for row in incoming:
                    persisted = deepcopy(row)
                    persisted.setdefault("id", str(uuid4()))
                    rows.append(persisted)
                    inserted.append(deepcopy(persisted))
                return FakeResult(data=inserted)

            if self._mode == "upsert":
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
                            persisted.setdefault("id", str(uuid4()))
                            rows.append(persisted)
                    else:
                        persisted.setdefault("id", str(uuid4()))
                        rows.append(persisted)
                    upserted.append(deepcopy(persisted))
                return FakeResult(data=upserted)

            if self._mode == "update":
                updated = []
                for row in matches:
                    row.update(deepcopy(self._payload))
                    updated.append(deepcopy(row))
                return FakeResult(data=updated)

            if self._mode == "delete":
                deleted = [deepcopy(row) for row in matches]
                self.db.tables[self.table_name] = [row for row in rows if not self._matches(row)]
                return FakeResult(data=deleted)

        raise AssertionError(f"Unsupported mode: {self._mode}")

    def _normalize_payload(self, payload: dict | list[dict]) -> list[dict]:
        if isinstance(payload, list):
            return payload
        return [payload]

    def _find_conflict(self, rows: list[dict], candidate: dict) -> dict | None:
        for row in rows:
            if all(str(row.get(key)) == str(candidate.get(key)) for key in self._upsert_conflict):
                return row
        return None

    def _apply_order(self, rows: list[dict]) -> list[dict]:
        if not self._order_key:
            return rows
        return sorted(rows, key=lambda row: row.get(self._order_key), reverse=self._order_desc)

    def _apply_range(self, rows: list[dict]) -> list[dict]:
        if self._range is None:
            return rows
        start, end = self._range
        return rows[start : end + 1]

    def _matches(self, row: dict) -> bool:
        for op, key, value in self._filters:
            current = row.get(key)
            if op == "eq" and current != value:
                return False
            if op == "in" and current not in value:
                return False
            if op == "gt" and not (current > value):
                return False
            if op == "gte" and not (current >= value):
                return False
            if op == "lt" and not (current < value):
                return False
            if op == "lte" and not (current <= value):
                return False
            if op == "ilike":
                pattern = str(value).replace("%", "").casefold()
                if pattern not in str(current or "").casefold():
                    return False
        return True


class FakeDB:
    def __init__(
        self,
        tables: dict[str, list[dict]] | None = None,
        *,
        rpc_failures: set[str] | None = None,
        table_failures: set[str] | None = None,
        restore_fail_table: str | None = None,
    ):
        self.tables = deepcopy(tables or {})
        self.rpc_failures = set(rpc_failures or set())
        self.table_failures = set(table_failures or set())
        self.restore_fail_table = restore_fail_table
        self._lock = Lock()

    def table(self, table_name: str) -> FakeTableQuery:
        return FakeTableQuery(self, table_name)

    def rpc(self, function_name: str, params: dict[str, Any]) -> FakeRPCQuery:
        return FakeRPCQuery(self, function_name, params)

    def execute_rpc(self, function_name: str, params: dict[str, Any]) -> FakeResult:
        with self._lock:
            if function_name in self.rpc_failures:
                raise RuntimeError(f"RPC failure injected: {function_name}")

            if function_name == "increment_legacy_auth_event_counter":
                return self._increment_legacy_auth_event_counter(params)
            if function_name == "claim_idempotency_key":
                return self._claim_idempotency_key(params)
            if function_name == "commit_idempotency_key":
                return self._commit_idempotency_key(params)
            if function_name == "fail_idempotency_key":
                return self._fail_idempotency_key(params)
            if function_name == "restore_device_backup_payload":
                return self._restore_device_backup_payload(params)
            if function_name == "complete_cooking_transaction":
                return self._complete_cooking_transaction(params)

        raise AssertionError(f"Unsupported rpc: {function_name}")

    def _increment_legacy_auth_event_counter(self, params: dict[str, Any]) -> FakeResult:
        table = self.tables.setdefault("legacy_auth_event_counters", [])
        auth_mode = str(params.get("p_auth_mode") or "")
        outcome = str(params.get("p_outcome") or "")
        reason = str(params.get("p_reason") or "")

        existing = next(
            (
                row
                for row in table
                if row.get("auth_mode") == auth_mode and row.get("outcome") == outcome and row.get("reason") == reason
            ),
            None,
        )
        if existing is None:
            table.append(
                {
                    "id": str(uuid4()),
                    "auth_mode": auth_mode,
                    "outcome": outcome,
                    "reason": reason,
                    "event_count": 1,
                    "first_observed_at": _now_iso(),
                    "last_observed_at": _now_iso(),
                }
            )
        else:
            existing["event_count"] = int(existing.get("event_count") or 0) + 1
            existing["last_observed_at"] = _now_iso()
        return FakeResult(data={"ok": True})

    def _find_idempotency_row(self, params: dict[str, Any]) -> dict | None:
        rows = self.tables.setdefault("idempotency_keys", [])
        for row in rows:
            if (
                row.get("device_id") == params.get("p_device_id")
                and row.get("method") == str(params.get("p_method") or "").upper()
                and row.get("path") == params.get("p_path")
                and row.get("idempotency_key") == params.get("p_idempotency_key")
            ):
                return row
        return None

    def _claim_idempotency_key(self, params: dict[str, Any]) -> FakeResult:
        rows = self.tables.setdefault("idempotency_keys", [])
        now = datetime.now(timezone.utc)
        request_fingerprint = params.get("p_request_fingerprint")
        lock_ttl_seconds = max(int(params.get("p_lock_ttl_seconds") or 0), 1)
        replay_ttl_seconds = max(int(params.get("p_replay_ttl_seconds") or 0), 1)
        row = self._find_idempotency_row(params)
        if row is None:
            rows.append(
                {
                    "id": str(uuid4()),
                    "device_id": params.get("p_device_id"),
                    "method": str(params.get("p_method") or "").upper(),
                    "path": params.get("p_path"),
                    "idempotency_key": params.get("p_idempotency_key"),
                    "request_fingerprint": request_fingerprint,
                    "status": "in_progress",
                    "locked_until": (now + timedelta(seconds=lock_ttl_seconds)).isoformat(),
                    "response_status": None,
                    "response_headers": {},
                    "response_body": {},
                    "failure_code": None,
                    "failure_message": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "expires_at": (now + timedelta(seconds=replay_ttl_seconds)).isoformat(),
                }
            )
            return FakeResult(data=[{"action": "started", "status": "in_progress", "retry_after_seconds": 0}])

        expires_at = _parse_iso(row.get("expires_at"))
        if expires_at and expires_at <= now:
            row.update(
                {
                    "request_fingerprint": request_fingerprint,
                    "status": "in_progress",
                    "locked_until": (now + timedelta(seconds=lock_ttl_seconds)).isoformat(),
                    "response_status": None,
                    "response_headers": {},
                    "response_body": {},
                    "failure_code": None,
                    "failure_message": None,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "expires_at": (now + timedelta(seconds=replay_ttl_seconds)).isoformat(),
                }
            )
            return FakeResult(data=[{"action": "started", "status": "in_progress", "retry_after_seconds": 0}])

        if str(row.get("request_fingerprint") or "") != str(request_fingerprint or ""):
            return FakeResult(
                data=[
                    {
                        "action": "conflict",
                        "status": row.get("status"),
                        "response_status": row.get("response_status"),
                        "response_headers": row.get("response_headers") or {},
                        "response_body": row.get("response_body") or {},
                        "retry_after_seconds": 0,
                    }
                ]
            )

        if row.get("status") == "committed":
            return FakeResult(
                data=[
                    {
                        "action": "replay",
                        "status": "committed",
                        "response_status": row.get("response_status"),
                        "response_headers": row.get("response_headers") or {},
                        "response_body": row.get("response_body") or {},
                        "retry_after_seconds": 0,
                    }
                ]
            )

        locked_until = _parse_iso(row.get("locked_until"))
        if row.get("status") == "in_progress" and locked_until and locked_until > now:
            retry_after = max(1, ceil((locked_until - now).total_seconds()))
            return FakeResult(
                data=[
                    {
                        "action": "in_progress",
                        "status": "in_progress",
                        "response_status": row.get("response_status"),
                        "response_headers": row.get("response_headers") or {},
                        "response_body": row.get("response_body") or {},
                        "retry_after_seconds": retry_after,
                    }
                ]
            )

        row.update(
            {
                "request_fingerprint": request_fingerprint,
                "status": "in_progress",
                "locked_until": (now + timedelta(seconds=lock_ttl_seconds)).isoformat(),
                "response_status": None,
                "response_headers": {},
                "response_body": {},
                "failure_code": None,
                "failure_message": None,
                "updated_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=replay_ttl_seconds)).isoformat(),
            }
        )
        return FakeResult(data=[{"action": "started", "status": "in_progress", "retry_after_seconds": 0}])

    def _commit_idempotency_key(self, params: dict[str, Any]) -> FakeResult:
        row = self._find_idempotency_row(params)
        if row is None:
            return FakeResult(data={"commit_idempotency_key": False})
        if row.get("status") != "in_progress":
            return FakeResult(data={"commit_idempotency_key": False})
        if str(row.get("request_fingerprint") or "") != str(params.get("p_request_fingerprint") or ""):
            return FakeResult(data={"commit_idempotency_key": False})

        now = datetime.now(timezone.utc)
        replay_ttl_seconds = max(int(params.get("p_replay_ttl_seconds") or 0), 1)
        row.update(
            {
                "status": "committed",
                "locked_until": None,
                "response_status": int(params.get("p_response_status") or 200),
                "response_headers": deepcopy(params.get("p_response_headers") or {}),
                "response_body": deepcopy(params.get("p_response_body") or {}),
                "updated_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=replay_ttl_seconds)).isoformat(),
            }
        )
        return FakeResult(data={"commit_idempotency_key": True})

    def _fail_idempotency_key(self, params: dict[str, Any]) -> FakeResult:
        row = self._find_idempotency_row(params)
        if row is None:
            return FakeResult(data={"fail_idempotency_key": False})
        row.update(
            {
                "status": "failed",
                "locked_until": None,
                "failure_code": params.get("p_failure_code"),
                "failure_message": params.get("p_failure_message"),
                "updated_at": _now_iso(),
            }
        )
        return FakeResult(data={"fail_idempotency_key": True})

    def _restore_device_backup_payload(self, params: dict[str, Any]) -> FakeResult:
        device_id = str(params.get("p_device_id") or "")
        mode = str(params.get("p_mode") or "merge")
        payload = params.get("p_payload") or {}
        working = deepcopy(self.tables)
        backup_tables = [
            "inventory",
            "shopping_items",
            "favorite_recipes",
            "cooking_history",
            "notifications",
            "inventory_logs",
            "price_history",
        ]

        if mode == "replace":
            for table_name in backup_tables:
                working[table_name] = [row for row in working.get(table_name, []) if row.get("device_id") != device_id]

        counts: dict[str, int] = {}
        try:
            counts["inventory"] = self._restore_inventory_rows(working, device_id, payload.get("inventory") or [])
            counts["shopping_items"] = self._restore_insert_rows(working, "shopping_items", device_id, payload.get("shopping_items") or [])
            counts["favorite_recipes"] = self._restore_favorite_rows(working, device_id, payload.get("favorite_recipes") or [])
            counts["cooking_history"] = self._restore_insert_rows(working, "cooking_history", device_id, payload.get("cooking_history") or [])
            counts["notifications"] = self._restore_insert_rows(working, "notifications", device_id, payload.get("notifications") or [])
            counts["inventory_logs"] = self._restore_insert_rows(working, "inventory_logs", device_id, payload.get("inventory_logs") or [])
            counts["price_history"] = self._restore_insert_rows(working, "price_history", device_id, payload.get("price_history") or [])
        except Exception:
            raise

        self.tables = working
        return FakeResult(data=counts)

    def _restore_inventory_rows(self, working: dict[str, list[dict]], device_id: str, rows: list[dict]) -> int:
        if self.restore_fail_table == "inventory":
            raise RuntimeError("Injected restore failure: inventory")
        table = working.setdefault("inventory", [])
        count = 0
        for row in rows:
            candidate = deepcopy(row)
            candidate["device_id"] = device_id
            existing = next(
                (
                    item
                    for item in table
                    if item.get("device_id") == device_id and item.get("name_normalized") == candidate.get("name_normalized")
                ),
                None,
            )
            if existing is None:
                candidate.setdefault("id", str(uuid4()))
                table.append(candidate)
            else:
                existing.update(candidate)
            count += 1
        return count

    def _restore_favorite_rows(self, working: dict[str, list[dict]], device_id: str, rows: list[dict]) -> int:
        if self.restore_fail_table == "favorite_recipes":
            raise RuntimeError("Injected restore failure: favorite_recipes")
        table = working.setdefault("favorite_recipes", [])
        count = 0
        for row in rows:
            candidate = deepcopy(row)
            candidate["device_id"] = device_id
            existing = next(
                (
                    item
                    for item in table
                    if item.get("device_id") == device_id and item.get("recipe_id") == candidate.get("recipe_id")
                ),
                None,
            )
            if existing is None:
                candidate.setdefault("id", str(uuid4()))
                table.append(candidate)
            else:
                existing.update(candidate)
            count += 1
        return count

    def _restore_insert_rows(self, working: dict[str, list[dict]], table_name: str, device_id: str, rows: list[dict]) -> int:
        if self.restore_fail_table == table_name:
            raise RuntimeError(f"Injected restore failure: {table_name}")
        table = working.setdefault(table_name, [])
        for row in rows:
            candidate = deepcopy(row)
            candidate["device_id"] = device_id
            candidate.setdefault("id", str(uuid4()))
            table.append(candidate)
        return len(rows)

    def _complete_cooking_transaction(self, params: dict[str, Any]) -> FakeResult:
        device_id = str(params.get("p_device_id") or "")
        updates = params.get("p_updates") or []
        delete_ids = {str(value) for value in (params.get("p_delete_ids") or [])}
        history_id = str(uuid4())
        inventory = self.tables.setdefault("inventory", [])
        for row in inventory:
            if row.get("device_id") != device_id:
                continue
            if str(row.get("id")) in delete_ids:
                row["_delete"] = True
                continue
            for update in updates:
                if str(update.get("id")) == str(row.get("id")):
                    row["quantity"] = update.get("quantity")
        self.tables["inventory"] = [row for row in inventory if not row.get("_delete")]
        self.tables.setdefault("cooking_history", []).append(
            {
                "id": history_id,
                "device_id": device_id,
                "recipe_id": params.get("p_recipe_id"),
                "recipe_title": params.get("p_recipe_title"),
                "servings": params.get("p_servings"),
                "deducted_items": deepcopy(params.get("p_deducted_items") or []),
                "cooked_at": _now_iso(),
            }
        )
        return FakeResult(data={"history_id": history_id})
