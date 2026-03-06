from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.idempotency import execute_idempotent_mutation
from app.core.normalization import NAME_NORMALIZATION_VERSION
from app.core.units import DEFAULT_UNIT
from app.services.backup.export_service import export_backup
from app.services.backup.restore_service import restore_backup

from .fakes import FakeDB


def test_export_backup_returns_only_device_scoped_rows() -> None:
    db = FakeDB(
        {
            "inventory": [
                {"id": "1", "device_id": "device-a", "name": "Milk"},
                {"id": "2", "device_id": "device-b", "name": "Eggs"},
            ],
            "shopping_items": [],
            "favorite_recipes": [],
            "cooking_history": [],
            "notifications": [],
            "inventory_logs": [],
            "price_history": [],
        }
    )

    result = export_backup(db, device_id="device-a")

    assert result.success is True
    assert result.payload["data"]["inventory"] == [{"id": "1", "device_id": "device-a", "name": "Milk"}]
    assert result.status.value == "ok"


def test_restore_backup_merge_normalizes_inventory_shopping_and_units() -> None:
    db = FakeDB(
        {
            "inventory": [],
            "shopping_items": [],
            "favorite_recipes": [],
            "cooking_history": [],
            "notifications": [],
            "inventory_logs": [],
            "price_history": [],
        }
    )
    payload = {
        "data": {
            "inventory": [{"name": "  Milk  ", "quantity": 2, "unit": "unit", "category": "냉장"}],
            "shopping_items": [{"name": "  ｍilk  ", "quantity": 3, "unit": ""}],
            "favorite_recipes": [{"recipe_id": "recipe-1", "title": "Soup", "recipe_data": {"ok": True}}],
        }
    }

    result = restore_backup(
        db,
        device_id="device-a",
        payload=payload,
        mode="merge",
    )

    assert result.success is True
    inventory_row = db.tables["inventory"][0]
    shopping_row = db.tables["shopping_items"][0]
    assert inventory_row["name_normalized"] == "milk"
    assert inventory_row["name_normalization_version"] == NAME_NORMALIZATION_VERSION
    assert inventory_row["unit"] == DEFAULT_UNIT
    assert shopping_row["name_normalized"] == "milk"
    assert shopping_row["name_normalization_version"] == NAME_NORMALIZATION_VERSION
    assert shopping_row["unit"] == DEFAULT_UNIT
    assert db.tables["favorite_recipes"][0]["recipe_id"] == "recipe-1"


def test_restore_backup_validation_failure_does_not_write_partial_rows() -> None:
    db = FakeDB(
        {
            "inventory": [{"id": "inv-1", "device_id": "device-a", "name": "Milk"}],
            "shopping_items": [],
            "favorite_recipes": [],
            "cooking_history": [],
            "notifications": [],
            "inventory_logs": [],
            "price_history": [],
        }
    )

    with pytest.raises(HTTPException) as excinfo:
        restore_backup(db, device_id="device-a", payload={"invalid": True}, mode="merge")

    assert excinfo.value.status_code == 400
    assert db.tables["inventory"] == [{"id": "inv-1", "device_id": "device-a", "name": "Milk"}]


def test_restore_backup_replace_is_atomic_when_insert_fails() -> None:
    tables = {
        "inventory": [{"id": "inv-1", "device_id": "device-a", "name": "Milk", "name_normalized": "milk"}],
        "shopping_items": [{"id": "shop-1", "device_id": "device-a", "name": "Eggs"}],
        "favorite_recipes": [],
        "cooking_history": [],
        "notifications": [],
        "inventory_logs": [],
        "price_history": [],
    }
    db = FakeDB(tables, restore_fail_table="shopping_items")
    payload = {
        "data": {
            "inventory": [{"name": "Rice", "name_normalized": "rice", "quantity": 1, "unit": "개"}],
            "shopping_items": [{"name": "Eggs", "name_normalized": "eggs", "quantity": 2, "unit": "개"}],
        }
    }

    with pytest.raises(HTTPException) as excinfo:
        restore_backup(db, device_id="device-a", payload=payload, mode="replace")

    assert excinfo.value.status_code == 500
    assert db.tables == tables


def test_restore_backup_duplicate_retry_replays_without_second_side_effect() -> None:
    async def run() -> None:
        db = FakeDB(
            {
                "idempotency_keys": [],
                "inventory": [],
                "shopping_items": [],
                "favorite_recipes": [],
                "cooking_history": [],
                "notifications": [],
                "inventory_logs": [],
                "price_history": [],
            }
        )
        payload = {"data": {"shopping_items": [{"name": "Milk", "quantity": 1, "unit": "개"}]}}

        first = await execute_idempotent_mutation(
            db,
            device_id="device-a",
            method="POST",
            path="/auth/backup/restore",
            idempotency_key="restore-1",
            request_payload={"payload": payload, "mode": "merge"},
            require_key=True,
            handler=lambda: restore_backup(db, device_id="device-a", payload=payload, mode="merge"),
        )

        replayed = await execute_idempotent_mutation(
            db,
            device_id="device-a",
            method="POST",
            path="/auth/backup/restore",
            idempotency_key="restore-1",
            request_payload={"payload": payload, "mode": "merge"},
            require_key=True,
            handler=lambda: restore_backup(db, device_id="device-a", payload=payload, mode="merge"),
        )

        assert first.success is True
        assert len(db.tables["shopping_items"]) == 1
        assert isinstance(replayed, JSONResponse)
        assert replayed.headers["x-idempotency-replayed"] == "true"
        assert replayed.body

    asyncio.run(run())
