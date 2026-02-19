from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_db, get_idempotency_store, get_supabase_client
from app.main import app
from app.schemas.schemas import FoodItem
from app.services.gemini_service import get_gemini_service

TEST_DEVICE_ID = "device-1234"
TEST_DEVICE_TOKEN = "test-device-token"
TEST_DEVICE_TOKEN_HASH = hashlib.sha256(TEST_DEVICE_TOKEN.encode("utf-8")).hexdigest()


def _load_env_file(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        loaded[key.strip()] = value.strip()
    return loaded


def pytest_configure() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env.test"
    for key, value in _load_env_file(env_path).items():
        os.environ[key] = value


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    get_supabase_client.cache_clear()
    get_idempotency_store.cache_clear()
    yield
    get_settings.cache_clear()
    get_supabase_client.cache_clear()
    get_idempotency_store.cache_clear()


@dataclass
class MockQueryResult:
    data: Any


class MockSupabaseTable:
    def __init__(self, client: "MockSupabaseClient", table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._action = "select"
        self._payload: Any = None
        self._filters: list[tuple[str, str, Any]] = []
        self._columns: list[str] | None = None
        self._single = False
        self._order_field: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._on_conflict: str | None = None

    def select(self, fields: str = "*") -> "MockSupabaseTable":
        self._action = "select"
        fields = fields.strip()
        self._columns = None if fields == "*" else [item.strip() for item in fields.split(",") if item.strip()]
        return self

    def insert(self, payload: dict | list[dict]) -> "MockSupabaseTable":
        self._action = "insert"
        self._payload = payload
        return self

    def upsert(self, payload: list[dict], on_conflict: str | None = None) -> "MockSupabaseTable":
        self._action = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload: dict) -> "MockSupabaseTable":
        self._action = "update"
        self._payload = payload
        return self

    def delete(self) -> "MockSupabaseTable":
        self._action = "delete"
        return self

    def eq(self, field: str, value: Any) -> "MockSupabaseTable":
        self._filters.append(("eq", field, value))
        return self

    def in_(self, field: str, values: Iterable[Any]) -> "MockSupabaseTable":
        self._filters.append(("in", field, list(values)))
        return self

    def gt(self, field: str, value: Any) -> "MockSupabaseTable":
        self._filters.append(("gt", field, value))
        return self

    def gte(self, field: str, value: Any) -> "MockSupabaseTable":
        self._filters.append(("gte", field, value))
        return self

    def lt(self, field: str, value: Any) -> "MockSupabaseTable":
        self._filters.append(("lt", field, value))
        return self

    def lte(self, field: str, value: Any) -> "MockSupabaseTable":
        self._filters.append(("lte", field, value))
        return self

    def ilike(self, field: str, pattern: str) -> "MockSupabaseTable":
        self._filters.append(("ilike", field, pattern))
        return self

    def order(self, field: str, desc: bool = False, nullsfirst: bool = False) -> "MockSupabaseTable":
        self._order_field = field
        self._order_desc = desc
        return self

    def range(self, start: int, end: int) -> "MockSupabaseTable":
        self._range = (start, end)
        return self

    def limit(self, count: int) -> "MockSupabaseTable":
        self._limit = count
        return self

    def single(self) -> "MockSupabaseTable":
        self._single = True
        return self

    def _matches_filters(self, row: dict) -> bool:
        for op, field, expected in self._filters:
            actual = row.get(field)
            if op == "eq" and actual != expected:
                return False
            if op == "in" and actual not in expected:
                return False
            if op == "gt" and not (actual is not None and actual > expected):
                return False
            if op == "gte" and not (actual is not None and actual >= expected):
                return False
            if op == "lt" and not (actual is not None and actual < expected):
                return False
            if op == "lte" and not (actual is not None and actual <= expected):
                return False
            if op == "ilike":
                if actual is None:
                    return False
                regex = re.escape(str(expected)).replace("%", ".*")
                if re.fullmatch(regex, str(actual), flags=re.IGNORECASE) is None:
                    return False
        return True

    def _project_columns(self, rows: list[dict]) -> list[dict]:
        if not self._columns:
            return rows
        return [{column: row.get(column) for column in self._columns} for row in rows]

    def _apply_order_and_paging(self, rows: list[dict]) -> list[dict]:
        if self._order_field:
            rows = sorted(rows, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._range:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self) -> MockQueryResult:
        table = self._client.tables.setdefault(self._table_name, [])

        if self._action == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            rows = [deepcopy(item) for item in payloads]
            table.extend(rows)
            return MockQueryResult(rows)

        if self._action == "upsert":
            rows = [deepcopy(item) for item in self._payload]
            conflict_fields = [field.strip() for field in (self._on_conflict or "").split(",") if field.strip()]
            if not conflict_fields:
                table.extend(rows)
                return MockQueryResult(rows)

            for incoming in rows:
                matched_index = None
                for index, existing in enumerate(table):
                    if all(existing.get(field) == incoming.get(field) for field in conflict_fields):
                        matched_index = index
                        break
                if matched_index is None:
                    table.append(incoming)
                else:
                    updated = deepcopy(table[matched_index])
                    updated.update(incoming)
                    table[matched_index] = updated
            return MockQueryResult(rows)

        matched_rows = [row for row in table if self._matches_filters(row)]

        if self._action == "update":
            for row in matched_rows:
                row.update(deepcopy(self._payload))
            return MockQueryResult([deepcopy(row) for row in matched_rows])

        if self._action == "delete":
            to_remove = set(id(row) for row in matched_rows)
            table[:] = [row for row in table if id(row) not in to_remove]
            return MockQueryResult([deepcopy(row) for row in matched_rows])

        rows_out = [deepcopy(row) for row in matched_rows]
        rows_out = self._apply_order_and_paging(rows_out)
        rows_out = self._project_columns(rows_out)
        if self._single:
            return MockQueryResult(rows_out[0] if rows_out else None)
        return MockQueryResult(rows_out)


class MockSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}

    def table(self, table_name: str) -> MockSupabaseTable:
        return MockSupabaseTable(self, table_name)


class MockGeminiService:
    def __init__(self) -> None:
        self.food_items: list[FoodItem] = []
        self.receipt_items: list[FoodItem] = []
        self.receipt_raw_text: str | None = None

    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> list[FoodItem]:
        return list(self.food_items)

    async def analyze_receipt_image(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> tuple[list[FoodItem], str | None]:
        return list(self.receipt_items), self.receipt_raw_text


@pytest.fixture
def mock_supabase() -> MockSupabaseClient:
    return MockSupabaseClient()


@pytest.fixture
def seed_supabase(mock_supabase: MockSupabaseClient):
    def _seed(table_name: str, rows: list[dict]) -> None:
        mock_supabase.tables[table_name] = [deepcopy(row) for row in rows]

    return _seed


@pytest.fixture
def mock_gemini_service() -> MockGeminiService:
    return MockGeminiService()


@pytest.fixture
def mock_fcm(monkeypatch: pytest.MonkeyPatch):
    sent_payloads: list[dict[str, Any]] = []

    def _fake_send_push_to_many(
        push_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> int:
        sent_payloads.append(
            {
                "push_tokens": list(push_tokens),
                "title": title,
                "body": body,
                "data": deepcopy(data) if data else {},
            }
        )
        return len(push_tokens)

    monkeypatch.setattr("app.api.admin.send_push_to_many", _fake_send_push_to_many)
    return sent_payloads


@pytest.fixture
def client(mock_supabase: MockSupabaseClient, mock_gemini_service: MockGeminiService):
    devices = mock_supabase.tables.setdefault("devices", [])
    if not any(str(row.get("device_id")) == TEST_DEVICE_ID for row in devices):
        devices.append(
            {
                "device_id": TEST_DEVICE_ID,
                "device_secret_hash": TEST_DEVICE_TOKEN_HASH,
                "platform": "test",
            }
        )

    app.dependency_overrides[get_db] = lambda: mock_supabase
    app.dependency_overrides[get_gemini_service] = lambda: mock_gemini_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
