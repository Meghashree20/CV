"""GET /health and application startup."""


def test_health_reports_process_and_mongodb(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["service"] == "Skin Analysis API"
    assert body["environment"] == "test"
    assert body["mongodb"] in {"connected", "unavailable"}
    if body["mongodb"] == "connected":
        assert body["status"] == "ok"
    else:
        assert body["status"] == "degraded"
    assert "mongodb://" not in response.text


def test_openapi_lists_health(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]


def test_cors_allows_configured_frontend_origin(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_does_not_reflect_unknown_origin(client):
    response = client.get("/health", headers={"Origin": "https://unknown.example"})

    assert "access-control-allow-origin" not in response.headers
