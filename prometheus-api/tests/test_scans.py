from app.schemas.schemas import FoodItem


def _auth_headers() -> dict[str, str]:
    return {
        "X-App-Token": "test-app-token",
        "X-Device-ID": "device-1234",
        "X-Device-Token": "test-device-token",
    }


def test_upload_size_limit_exceeded_returns_413(client) -> None:
    oversized_image = b"x" * (1024 * 1024 + 1)

    response = client.post(
        "/scans/upload",
        headers=_auth_headers(),
        files={"file": ("too-large.jpg", oversized_image, "image/jpeg")},
    )

    assert response.status_code == 413
    assert "Maximum allowed size is 1MB" in response.json()["detail"]


def test_upload_scan_success_returns_completed_status(client, mock_gemini_service, mock_supabase) -> None:
    mock_gemini_service.food_items = [
        FoodItem(name="우유", quantity=1, unit="L", category="냉장", confidence=0.99),
    ]

    response = client.post(
        "/scans/upload",
        headers=_auth_headers(),
        files={"file": ("ok.jpg", b"tiny-image", "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["scan_id"]

    scan_id = body["scan_id"]
    result = client.get(f"/scans/{scan_id}/result", headers=_auth_headers())
    assert result.status_code == 200
    assert len(result.json()["items"]) == 1

    stored_scan = mock_supabase.tables["scans"][0]
    assert stored_scan["status"] == "completed"


def test_upload_scan_rejects_non_image_file(client) -> None:
    response = client.post(
        "/scans/upload",
        headers=_auth_headers(),
        files={"file": ("doc.txt", b"plain-text", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_scan_marks_failed_when_gemini_raises(client, mock_gemini_service, mock_supabase) -> None:
    async def _boom(image_bytes: bytes, mime_type: str = "image/jpeg"):
        raise RuntimeError("gemini unavailable")

    mock_gemini_service.analyze_food_image = _boom

    response = client.post(
        "/scans/upload",
        headers=_auth_headers(),
        files={"file": ("broken.jpg", b"tiny-image", "image/jpeg")},
    )

    assert response.status_code == 502
    assert mock_supabase.tables["scans"][0]["status"] == "failed"
