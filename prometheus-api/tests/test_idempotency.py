from __future__ import annotations

from app.core.idempotency import load_idempotent_response, save_idempotent_response


def _auth_headers(idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-App-ID": "prometheus-app",
        "X-Device-ID": "device-1234",
        "X-Device-Token": "test-device-token",
    }
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    return headers


def test_idempotency_store_roundtrip(mock_supabase) -> None:
    save_idempotent_response(
        mock_supabase,
        device_id="device-1234",
        method="POST",
        path="/inventory/bulk",
        idempotency_key="idem-1",
        status_code=200,
        payload={"ok": True},
    )
    replayed = load_idempotent_response(
        mock_supabase,
        device_id="device-1234",
        method="POST",
        path="/inventory/bulk",
        idempotency_key="idem-1",
    )
    assert replayed is not None
    assert replayed.status_code == 200


def test_inventory_bulk_replays_on_same_idempotency_key(client, mock_supabase) -> None:
    payload = {
        "items": [
            {
                "name": "우유",
                "quantity": 1,
                "unit": "개",
                "category": "냉장",
                "confidence": 0.9,
            }
        ]
    }

    first = client.post("/inventory/bulk", headers=_auth_headers("idem-key-1"), json=payload)
    second = client.post("/inventory/bulk", headers=_auth_headers("idem-key-1"), json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("X-Idempotency-Replayed") == "true"

    inventory_rows = mock_supabase.tables.get("inventory") or []
    assert len(inventory_rows) == 1
