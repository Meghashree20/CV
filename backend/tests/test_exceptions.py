"""Exception handlers hide internal failures and shape expected errors."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import AppError
from app.main import create_app


def _client_with(route_setup) -> TestClient:
    application: FastAPI = create_app()
    route_setup(application)
    return TestClient(application, raise_server_exceptions=False)


def test_app_error_uses_public_code():
    def setup(application: FastAPI) -> None:
        @application.get("/_raise")
        async def raise_app_error():
            raise AppError("The requested record was not found", status_code=404, code="not_found")

    with _client_with(setup) as client:
        response = client.get("/_raise")

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "The requested record was not found",
    }


def test_unexpected_error_hides_exception_text():
    def setup(application: FastAPI) -> None:
        @application.get("/_boom")
        async def boom():
            raise RuntimeError("mongodb://user:secret@internal:27017")

    with _client_with(setup) as client:
        response = client.get("/_boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error"
    assert body["message"] == "An unexpected error occurred"
    assert "secret" not in response.text
    assert "mongodb://" not in response.text


def test_validation_error_omits_raw_input():
    def setup(application: FastAPI) -> None:
        @application.get("/_need-int")
        async def need_int(count: int):
            return {"count": count}

    with _client_with(setup) as client:
        response = client.get("/_need-int", params={"count": "not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]
    assert "input" not in body["details"][0]
