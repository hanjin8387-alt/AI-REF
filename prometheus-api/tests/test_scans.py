def test_upload_size_limit_exceeded_returns_413(client) -> None:
    oversized_image = b"x" * (1024 * 1024 + 1)

    response = client.post(
        "/scans/upload",
        headers={
            "X-App-Token": "test-app-token",
            "X-Device-ID": "device-1234",
        },
        files={"file": ("too-large.jpg", oversized_image, "image/jpeg")},
    )

    assert response.status_code == 413
    assert "최대 1MB" in response.json()["detail"]
