from __future__ import annotations


def _auth_headers() -> dict[str, str]:
    return {
        "X-App-ID": "prometheus-app",
        "X-Device-ID": "device-1234",
        "X-Device-Token": "test-device-token",
    }


def test_backup_export_returns_table_results(client, seed_supabase) -> None:
    seed_supabase(
        "inventory",
        [
            {
                "id": "inv-1",
                "device_id": "device-1234",
                "name": "우유",
                "name_normalized": "우유",
                "quantity": 1,
                "unit": "개",
                "category": "냉장",
            }
        ],
    )

    response = client.get("/auth/backup/export", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "table_results" in body
    assert any(item["table"] == "inventory" for item in body["table_results"])


def test_backup_restore_rejects_invalid_mode(client) -> None:
    response = client.post(
        "/auth/backup/restore",
        headers=_auth_headers(),
        json={"payload": {"data": {}}, "mode": "invalid"},
    )
    assert response.status_code == 400
    assert "mode must be either merge or replace" in response.json()["detail"]
