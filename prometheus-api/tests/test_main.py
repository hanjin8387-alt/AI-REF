from uuid import UUID


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
    }


def test_request_id_header_is_generated_when_missing(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert str(UUID(request_id)) == request_id


def test_request_id_header_uses_incoming_value(client) -> None:
    response = client.get("/", headers={"X-Request-ID": "req-12345"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-12345"


def test_process_time_headers_are_present(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    process_time = response.headers.get("X-Process-Time")
    response_time = response.headers.get("X-Response-Time")
    assert process_time is not None
    assert response_time is not None
    assert float(process_time) >= 0
    assert float(response_time) >= 0


def test_cache_control_header_is_present_for_get_requests(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "private, max-age=15, stale-while-revalidate=30"
