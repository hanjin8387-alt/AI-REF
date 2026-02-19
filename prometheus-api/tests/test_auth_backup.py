from __future__ import annotations


def _auth_headers() -> dict[str, str]:
    return {
        "X-App-Token": "test-app-token",
        "X-Device-ID": "device-1234",
        "X-Device-Token": "test-device-token",
    }


def test_bootstrap_returns_device_registration_status(client, seed_supabase) -> None:
    seed_supabase(
        "devices",
        [
            {
                "device_id": "device-1234",
                "platform": "web",
            }
        ],
    )

    response = client.get("/auth/bootstrap", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_ok"] is True
    assert payload["token_required"] is True
    assert payload["device_registered"] is True
    assert payload["sync_pending_count"] == 0


def test_bootstrap_returns_unregistered_when_missing(client) -> None:
    headers = {**_auth_headers(), "X-Device-ID": "device-missing"}
    response = client.get("/auth/bootstrap", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_ok"] is True
    assert payload["device_registered"] is False


def test_backup_export_returns_payload_with_tables(client, seed_supabase) -> None:
    seed_supabase(
        "inventory",
        [
            {
                "id": "inv-1",
                "device_id": "device-1234",
                "name": "우유",
                "quantity": 1,
                "unit": "개",
                "expiry_date": None,
                "category": "냉장",
                "created_at": None,
                "updated_at": None,
            }
        ],
    )

    response = client.get("/auth/backup/export", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["payload"]["version"] == "backup-v1"
    assert "inventory" in payload["payload"]["data"]


def test_backup_restore_merge_returns_restored_counts(client) -> None:
    restore_payload = {
        "version": "backup-v1",
        "device_id": "old-device",
        "data": {
            "inventory": [
                {
                    "name": "토마토",
                    "quantity": 2,
                    "unit": "개",
                    "expiry_date": None,
                    "category": "상온",
                }
            ],
            "favorite_recipes": [
                {
                    "recipe_id": "r-1",
                    "title": "샐러드",
                    "recipe_data": {"title": "샐러드"},
                }
            ],
        },
    }

    response = client.post(
        "/auth/backup/restore",
        headers=_auth_headers(),
        json={"payload": restore_payload, "mode": "merge"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["restored_counts"]["inventory"] == 1
    assert payload["restored_counts"]["favorite_recipes"] == 1


def test_backup_restore_rejects_invalid_mode(client) -> None:
    response = client.post(
        "/auth/backup/restore",
        headers=_auth_headers(),
        json={"payload": {"data": {}}, "mode": "invalid"},
    )

    assert response.status_code == 400
    assert "mode must be either merge or replace" in response.json()["detail"]
