from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.api.inventory import get_inventory
from app.api.recipes import get_favorite_recipes
from app.api.shopping import get_shopping_items


@dataclass
class _FakeResult:
    data: list[dict[str, Any]]
    count: int


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, str, Any]] = []
        self._order_field: str | None = None
        self._order_desc = False
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field: str, value: Any):
        self._filters.append(("eq", field, value))
        return self

    def gte(self, field: str, value: Any):
        self._filters.append(("gte", field, value))
        return self

    def order(self, field: str, desc: bool = False, nullsfirst: bool = False):  # noqa: ARG002
        self._order_field = field
        self._order_desc = desc
        return self

    def range(self, start: int, end: int):
        self._range = (start, end)
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def execute(self):
        rows = [row for row in self._rows if self._matches_filters(row)]
        count = len(rows)

        if self._order_field:
            rows = sorted(rows, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._range:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]

        return _FakeResult(data=list(rows), count=count)

    def _matches_filters(self, row: dict[str, Any]) -> bool:
        for op, field, expected in self._filters:
            actual = row.get(field)
            if op == "eq" and actual != expected:
                return False
            if op == "gte" and not self._gte(actual, expected):
                return False
        return True

    @staticmethod
    def _to_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _gte(self, actual: Any, expected: Any) -> bool:
        actual_dt = self._to_datetime(actual)
        expected_dt = self._to_datetime(expected)
        if actual_dt is not None and expected_dt is not None:
            return actual_dt >= expected_dt
        return str(actual) >= str(expected)


class _FakeDb:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self._tables = tables

    def table(self, table_name: str):
        return _FakeQuery(self._tables.get(table_name, []))


def _recipe_payload(recipe_id: str, title: str) -> dict[str, Any]:
    return {
        "id": recipe_id,
        "title": title,
        "description": f"{title} description",
        "image_url": None,
        "cooking_time_minutes": 10,
        "difficulty": "easy",
        "servings": 1,
        "ingredients": [{"name": "egg", "quantity": 1, "unit": "ea", "available": True}],
        "instructions": ["mix and cook"],
        "priority_score": 0.7,
        "is_favorite": True,
    }


def test_inventory_updated_since_filters_and_sorts_by_updated_at() -> None:
    db = _FakeDb(
        {
            "inventory": [
                {
                    "id": "inv-old",
                    "device_id": "device-1",
                    "name": "potato",
                    "quantity": 1,
                    "unit": "ea",
                    "created_at": "2026-02-01T00:00:00+00:00",
                    "updated_at": "2026-02-01T00:00:00+00:00",
                },
                {
                    "id": "inv-new",
                    "device_id": "device-1",
                    "name": "onion",
                    "quantity": 2,
                    "unit": "ea",
                    "created_at": "2026-02-12T00:00:00+00:00",
                    "updated_at": "2026-02-12T00:00:00+00:00",
                },
                {
                    "id": "inv-other-device",
                    "device_id": "device-2",
                    "name": "milk",
                    "quantity": 1,
                    "unit": "pack",
                    "created_at": "2026-02-12T00:00:00+00:00",
                    "updated_at": "2026-02-12T00:00:00+00:00",
                },
            ]
        }
    )

    response = asyncio.run(
        get_inventory(
            category=None,
            sort_by="updated_at",
            limit=30,
            offset=0,
            updated_since=datetime(2026, 2, 10, tzinfo=timezone.utc),
            device_id="device-1",
            db=db,
        )
    )

    assert response.total_count == 1
    assert [item.id for item in response.items] == ["inv-new"]


def test_favorite_recipes_updated_since_filters_rows() -> None:
    db = _FakeDb(
        {
            "favorite_recipes": [
                {
                    "id": "fav-old",
                    "device_id": "device-1",
                    "recipe_id": "recipe-old",
                    "title": "old recipe",
                    "recipe_data": _recipe_payload("recipe-old", "old recipe"),
                    "created_at": "2026-02-01T00:00:00+00:00",
                },
                {
                    "id": "fav-new",
                    "device_id": "device-1",
                    "recipe_id": "recipe-new",
                    "title": "new recipe",
                    "recipe_data": _recipe_payload("recipe-new", "new recipe"),
                    "created_at": "2026-02-12T00:00:00+00:00",
                },
            ]
        }
    )

    response = asyncio.run(
        get_favorite_recipes(
            limit=30,
            offset=0,
            updated_since=datetime(2026, 2, 10, tzinfo=timezone.utc),
            device_id="device-1",
            db=db,
        )
    )

    assert response.total_count == 1
    assert [recipe.id for recipe in response.recipes] == ["recipe-new"]


def test_shopping_updated_since_filters_items_but_keeps_counts() -> None:
    db = _FakeDb(
        {
            "shopping_items": [
                {
                    "id": "shop-old",
                    "device_id": "device-1",
                    "name": "tofu",
                    "quantity": 1,
                    "unit": "block",
                    "status": "pending",
                    "source": "manual",
                    "recipe_id": None,
                    "recipe_title": None,
                    "added_to_inventory": False,
                    "purchased_at": None,
                    "created_at": "2026-02-01T00:00:00+00:00",
                    "updated_at": "2026-02-01T00:00:00+00:00",
                },
                {
                    "id": "shop-new",
                    "device_id": "device-1",
                    "name": "ramen",
                    "quantity": 2,
                    "unit": "ea",
                    "status": "pending",
                    "source": "manual",
                    "recipe_id": None,
                    "recipe_title": None,
                    "added_to_inventory": False,
                    "purchased_at": None,
                    "created_at": "2026-02-12T00:00:00+00:00",
                    "updated_at": "2026-02-12T00:00:00+00:00",
                },
                {
                    "id": "shop-purchased",
                    "device_id": "device-1",
                    "name": "milk",
                    "quantity": 1,
                    "unit": "pack",
                    "status": "purchased",
                    "source": "manual",
                    "recipe_id": None,
                    "recipe_title": None,
                    "added_to_inventory": False,
                    "purchased_at": "2026-02-12T00:00:00+00:00",
                    "created_at": "2026-02-12T00:00:00+00:00",
                    "updated_at": "2026-02-12T00:00:00+00:00",
                },
            ]
        }
    )

    response = asyncio.run(
        get_shopping_items(
            status_filter=None,
            limit=30,
            offset=0,
            updated_since=datetime(2026, 2, 10, tzinfo=timezone.utc),
            device_id="device-1",
            db=db,
        )
    )

    assert [item.id for item in response.items] == ["shop-new", "shop-purchased"]
    assert response.pending_count == 2
    assert response.purchased_count == 1
