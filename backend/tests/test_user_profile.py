
"""Tests for authenticated user profile management."""

import pytest

from app.core.dependencies import get_current_user
from app.main import create_app
from app.api.routes.users import user_service


class FakeUserRepository:
    def __init__(self):
        self.user = {
            "_id": "profile-user-1",
            "name": "Alice",
            "email": "alice@example.com",
            "hashed_password": "secret-hash",
            "age": 22,
            "gender": "female",
            "skin_type": "oily",
            "skin_concerns": ["acne"],
            "skincare_goals": ["clear skin"],
        }

    async def get_by_id(self, user_id):
        if user_id == str(self.user["_id"]):
            return self.user
        return None

    async def update_profile(self, user_id, update_data):
        if user_id != str(self.user["_id"]):
            return None

        self.user.update(update_data)
        return self.user


@pytest.fixture
def profile_setup(client, monkeypatch):
    repo = FakeUserRepository()

    monkeypatch.setattr(user_service, "repo", repo)

    current_user = {
        "_id": "profile-user-1",
        "name": "Alice",
        "email": "alice@example.com",
    }

    client.app.dependency_overrides[get_current_user] = (
        lambda: current_user
    )

    yield repo

    client.app.dependency_overrides.clear()


def test_get_my_profile(client, profile_setup):
    response = client.get("/users/me")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["age"] == 22
    assert data["skin_type"] == "oily"


def test_update_name(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"name": "Alice Smith"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Alice Smith"


def test_update_multiple_fields(client, profile_setup):
    response = client.put(
        "/users/me",
        json={
            "age": 24,
            "skin_type": "dry",
            "skin_concerns": ["acne", "pigmentation"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["age"] == 24
    assert data["skin_type"] == "dry"
    assert data["skin_concerns"] == ["acne", "pigmentation"]


def test_clear_optional_field(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"skin_type": None},
    )

    assert response.status_code == 200
    assert response.json()["skin_type"] is None


def test_empty_update_returns_400(client, profile_setup):
    response = client.put("/users/me", json={})

    assert response.status_code == 400


def test_null_name_returns_422(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"name": None},
    )

    assert response.status_code == 422


def test_invalid_age_returns_422(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"age": 150},
    )

    assert response.status_code == 422


def test_invalid_skin_type_returns_422(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"skin_type": "unknown"},
    )

    assert response.status_code == 422


def test_email_cannot_be_updated(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"email": "new@example.com"},
    )

    assert response.status_code == 422


def test_password_cannot_be_updated(client, profile_setup):
    response = client.put(
        "/users/me",
        json={"password": "newpassword"},
    )

    assert response.status_code == 422


def test_password_hash_not_returned(client, profile_setup):
    response = client.get("/users/me")

    assert response.status_code == 200
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()


def test_missing_token_returns_401(client, profile_setup):
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get("/users/me")

    assert response.status_code == 401


def test_invalid_token_returns_401(client, profile_setup):
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid.token.signature"},
    )

    assert response.status_code == 401
