from __future__ import annotations

import hashlib
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_db, get_supabase_client
from app.main import app
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
    yield
    get_settings.cache_clear()
    get_supabase_client.cache_clear()


@dataclass
class MockQueryResult:
    data: Any
    count: int | None = None


class MockSupabaseTable:
    def __init__(self, client: "MockSupabaseClient", table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._action = "select"
        self._payload: Any = None
        self._filters: list[tuple[str, str, Any]] = []
        self._columns: list[str] | None = None
        self._single = False
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None
        self._order_field: str | None = None
        self._order_desc = False
        self._on_conflict: str | None = None
        self._count: bool = False

    def select(self, fields: str = "*", count: str | None = None) -> "MockSupabaseTable":
        self._action = "select"
        fields = fields.strip()
        self._columns = None if fields == "*" else [item.strip() for item in fields.split(",") if item.strip()]
        self._count = count == "exact"
        return self

    def insert(self, payload: dict | list[dict]) -> "MockSupabaseTable":
        self._action = "insert"
        self._payload = payload
        return self

    def upsert(self, payload: dict | list[dict], on_conflict: str | None = None) -> "MockSupabaseTable":
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

    def in_(self, field: str, values: list[Any]) -> "MockSupabaseTable":
        self._filters.append(("in", field, values))
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

    def _matches(self, row: dict[str, Any]) -> bool:
        for op, field, value in self._filters:
            actual = row.get(field)
            if op == "eq" and actual != value:
                return False
            if op == "in" and actual not in value:
                return False
            if op == "gt" and not (actual is not None and actual > value):
                return False
            if op == "gte" and not (actual is not None and actual >= value):
                return False
            if op == "lt" and not (actual is not None and actual < value):
                return False
        return True

    def execute(self) -> MockQueryResult:
        table = self._client.tables.setdefault(self._table_name, [])

        if self._action == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            rows = [deepcopy(item) for item in payloads]
            table.extend(rows)
            return MockQueryResult(data=rows, count=len(rows))

        if self._action == "upsert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            rows = [deepcopy(item) for item in payloads]
            conflict_fields = [field.strip() for field in (self._on_conflict or "").split(",") if field.strip()]
            if not conflict_fields:
                table.extend(rows)
                return MockQueryResult(data=rows, count=len(rows))

            for incoming in rows:
                matched_idx = None
                for idx, existing in enumerate(table):
                    if all(existing.get(field) == incoming.get(field) for field in conflict_fields):
                        matched_idx = idx
                        break
                if matched_idx is None:
                    table.append(incoming)
                else:
                    updated = deepcopy(table[matched_idx])
                    updated.update(incoming)
                    table[matched_idx] = updated
            return MockQueryResult(data=rows, count=len(rows))

        matched = [row for row in table if self._matches(row)]
        total_count = len(matched)

        if self._action == "update":
            for row in matched:
                row.update(deepcopy(self._payload))
            return MockQueryResult(data=[deepcopy(row) for row in matched], count=len(matched))

        if self._action == "delete":
            to_delete = {id(row) for row in matched}
            table[:] = [row for row in table if id(row) not in to_delete]
            return MockQueryResult(data=[deepcopy(row) for row in matched], count=len(matched))

        rows_out = [deepcopy(row) for row in matched]
        if self._order_field:
            rows_out = sorted(rows_out, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._range:
            start, end = self._range
            rows_out = rows_out[start : end + 1]
        if self._limit is not None:
            rows_out = rows_out[: self._limit]
        if self._columns:
            rows_out = [{column: row.get(column) for column in self._columns} for row in rows_out]
        if self._single:
            return MockQueryResult(data=rows_out[0] if rows_out else None, count=1 if rows_out else 0)
        return MockQueryResult(data=rows_out, count=total_count if self._count else None)


class MockSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def table(self, table_name: str) -> MockSupabaseTable:
        return MockSupabaseTable(self, table_name)

    def rpc(self, func_name: str, params: dict[str, Any]):  # pragma: no cover - minimal fallback
        class _RPC:
            def execute(self_inner):
                return MockQueryResult(data={"result": "rpc-ok"})

        return _RPC()


class MockGeminiService:
    async def analyze_food_image(self, image_bytes: bytes, mime_type: str = "image/jpeg"):
        from app.schemas.schemas import FoodItem

        return [FoodItem(name="우유", quantity=1, unit="개", category="냉장", confidence=0.8)]

    async def analyze_receipt_image(self, image_bytes: bytes, mime_type: str = "image/jpeg"):
        from app.schemas.schemas import FoodItem

        return ([FoodItem(name="사과", quantity=1, unit="개", category="상온", confidence=0.9)], "receipt raw")

    async def generate_recipe_recommendations(self, inventory_items, max_recipes: int = 5):
        return [
            {
                "id": "recipe_1",
                "title": "우유 스무디",
                "description": "간단 레시피",
                "recommendation_reason": "재고 활용",
                "cooking_time_minutes": 5,
                "difficulty": "easy",
                "servings": 1,
                "ingredients": [{"name": "우유", "quantity": 1, "unit": "개"}],
                "instructions": ["섞기"],
                "priority_score": 0.9,
            }
        ]


@pytest.fixture
def mock_supabase() -> MockSupabaseClient:
    return MockSupabaseClient()


@pytest.fixture
def seed_supabase(mock_supabase: MockSupabaseClient):
    def _seed(table_name: str, rows: list[dict[str, Any]]) -> None:
        mock_supabase.tables[table_name] = [deepcopy(row) for row in rows]

    return _seed


@pytest.fixture
def client(mock_supabase: MockSupabaseClient):
    now_iso = "2099-01-01T00:00:00+00:00"
    mock_supabase.tables.setdefault("devices", []).append(
        {
            "device_id": TEST_DEVICE_ID,
            "device_secret_hash": TEST_DEVICE_TOKEN_HASH,
            "token_version": 1,
            "token_expires_at": now_iso,
            "token_revoked_at": None,
            "last_used_at": None,
        }
    )
    app.dependency_overrides[get_db] = lambda: mock_supabase
    app.dependency_overrides[get_gemini_service] = lambda: MockGeminiService()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
