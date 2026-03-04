from __future__ import annotations


def test_authenticated_happy_path_bootstrap(client) -> None:
    response = client.get(
        "/auth/bootstrap",
        headers={
            "X-App-ID": "prometheus-app",
            "X-Device-ID": "device-1234",
            "X-Device-Token": "test-device-token",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_ok"] is True
    assert payload["device_registered"] is True


def test_authenticated_failure_path_requires_app_identity(client) -> None:
    response = client.get(
        "/auth/bootstrap",
        headers={
            "X-Device-ID": "device-1234",
            "X-Device-Token": "test-device-token",
        },
    )
    assert response.status_code == 401
