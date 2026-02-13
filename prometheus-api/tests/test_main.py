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
