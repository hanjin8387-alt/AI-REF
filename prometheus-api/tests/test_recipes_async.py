import time


def _auth_headers() -> dict[str, str]:
    return {
        "X-App-Token": "test-app-token",
        "X-Device-ID": "device-1234",
        "X-Device-Token": "test-device-token",
    }


def test_recommendation_job_polling_completes(client, mock_supabase, mock_gemini_service) -> None:
    mock_supabase.tables["inventory"] = [
        {
            "id": "inv-1",
            "device_id": "device-1234",
            "name": "계란",
            "quantity": 3,
            "unit": "개",
            "expiry_date": None,
            "category": "냉장",
        }
    ]

    async def _fake_generate(_inventory_items, max_recipes=5):
        return [
            {
                "id": "generated-recipe-1",
                "title": "계란말이",
                "description": "간단한 계란 요리",
                "cooking_time_minutes": 10,
                "difficulty": "easy",
                "servings": 1,
                "ingredients": [{"name": "계란", "quantity": 2, "unit": "개"}],
                "instructions": ["계란을 푼다", "팬에 익힌다"],
                "priority_score": 0.9,
            }
        ][:max_recipes]

    mock_gemini_service.generate_recipe_recommendations = _fake_generate

    create_resp = client.post("/recipes/recommendations/jobs?limit=1", headers=_auth_headers())
    assert create_resp.status_code == 200
    job_id = create_resp.json()["job_id"]
    assert job_id

    for _ in range(20):
        status_resp = client.get(f"/recipes/recommendations/jobs/{job_id}", headers=_auth_headers())
        assert status_resp.status_code == 200
        payload = status_resp.json()
        if payload["status"] == "completed":
            assert payload["total_count"] == 1
            assert payload["recipes"][0]["title"] == "계란말이"
            return
        assert payload["status"] in {"pending", "processing"}
        time.sleep(0.05)

    raise AssertionError("Recommendation job did not complete in time")


def test_recommendation_job_status_returns_404_for_unknown_job(client) -> None:
    response = client.get("/recipes/recommendations/jobs/non-existent-job", headers=_auth_headers())
    assert response.status_code == 404
