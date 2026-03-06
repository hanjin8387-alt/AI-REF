from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.idempotency import (
    IDEMPOTENCY_STATUS_HEADER,
    build_request_fingerprint,
    execute_idempotent_mutation,
)

from .fakes import FakeDB


def test_execute_idempotent_mutation_replays_committed_response() -> None:
    async def run() -> None:
        db = FakeDB({"idempotency_keys": []})

        first = await execute_idempotent_mutation(
            db,
            device_id="device-1",
            method="POST",
            path="/inventory/bulk",
            idempotency_key="key-1",
            request_payload={"name": "Milk"},
            handler=lambda: {"ok": True},
        )
        assert first == {"ok": True}

        replayed = await execute_idempotent_mutation(
            db,
            device_id="device-1",
            method="POST",
            path="/inventory/bulk",
            idempotency_key="key-1",
            request_payload={"name": "Milk"},
            handler=lambda: {"ok": False},
        )

        assert isinstance(replayed, JSONResponse)
        assert replayed.headers["x-idempotency-replayed"] == "true"
        assert replayed.headers[IDEMPOTENCY_STATUS_HEADER.lower()] == "replay"
        assert replayed.body == b'{"ok":true}'

    asyncio.run(run())


def test_execute_idempotent_mutation_returns_conflict_for_different_payload() -> None:
    async def run() -> None:
        db = FakeDB({"idempotency_keys": []})

        await execute_idempotent_mutation(
            db,
            device_id="device-1",
            method="POST",
            path="/inventory/bulk",
            idempotency_key="key-1",
            request_payload={"name": "Milk"},
            handler=lambda: {"ok": True},
        )

        try:
            await execute_idempotent_mutation(
                db,
                device_id="device-1",
                method="POST",
                path="/inventory/bulk",
                idempotency_key="key-1",
                request_payload={"name": "Eggs"},
                handler=lambda: {"ok": True},
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail == {
                "code": "idempotency_key_conflict",
                "message": "The idempotency key is already associated with a different request payload.",
            }
            assert exc.headers == {IDEMPOTENCY_STATUS_HEADER: "conflict"}
            return
        raise AssertionError("Expected HTTPException")

    asyncio.run(run())


def test_execute_idempotent_mutation_blocks_while_same_key_is_in_progress() -> None:
    async def run() -> None:
        db = FakeDB({"idempotency_keys": []})
        release = asyncio.Event()
        side_effects = 0

        async def slow_handler() -> dict[str, bool]:
            nonlocal side_effects
            side_effects += 1
            await release.wait()
            return {"ok": True}

        task = asyncio.create_task(
            execute_idempotent_mutation(
                db,
                device_id="device-1",
                method="POST",
                path="/shopping/items",
                idempotency_key="key-1",
                request_payload={"items": ["Milk"]},
                handler=slow_handler,
            )
        )
        await asyncio.sleep(0.01)

        try:
            await execute_idempotent_mutation(
                db,
                device_id="device-1",
                method="POST",
                path="/shopping/items",
                idempotency_key="key-1",
                request_payload={"items": ["Milk"]},
                handler=lambda: {"ok": False},
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail == {
                "code": "idempotency_in_progress",
                "message": "A matching request is already in progress.",
            }
            assert int(exc.headers["Retry-After"]) >= 1
            assert exc.headers[IDEMPOTENCY_STATUS_HEADER] == "in_progress"
        else:
            raise AssertionError("Expected HTTPException")

        release.set()
        result = await task
        assert result == {"ok": True}
        assert side_effects == 1

    asyncio.run(run())


def test_execute_idempotent_mutation_reclaims_stale_in_progress_claim() -> None:
    async def run() -> None:
        fingerprint = build_request_fingerprint({"items": ["Milk"]})
        stale_time = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        db = FakeDB(
            {
                "idempotency_keys": [
                    {
                        "id": "existing",
                        "device_id": "device-1",
                        "method": "POST",
                        "path": "/shopping/items",
                        "idempotency_key": "key-1",
                        "request_fingerprint": fingerprint,
                        "status": "in_progress",
                        "locked_until": stale_time,
                        "response_status": None,
                        "response_headers": {},
                        "response_body": {},
                        "created_at": stale_time,
                        "updated_at": stale_time,
                        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    }
                ]
            }
        )

        result = await execute_idempotent_mutation(
            db,
            device_id="device-1",
            method="POST",
            path="/shopping/items",
            idempotency_key="key-1",
            request_payload={"items": ["Milk"]},
            handler=lambda: {"ok": True},
        )

        assert result == {"ok": True}
        row = db.tables["idempotency_keys"][0]
        assert row["status"] == "committed"
        assert row["response_body"] == {"ok": True}

    asyncio.run(run())
