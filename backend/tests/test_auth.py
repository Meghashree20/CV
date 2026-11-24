import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.core.security import decode_access_token

# The client fixture is defined in ``backend/tests/conftest.py``
@pytest.fixture(autouse=True)
def mock_user_repository(monkeypatch):
    """Replace ``UserRepository`` with an in‑memory fake.

    The fake stores user documents in a simple dict keyed by the generated
    ``_id`` (a string). It implements the async methods used by the service
    layer: ``create_user``, ``find_by_email`` and ``get_by_id``.
    """

    class FakeRepository:
        _data = {}
        _id_counter = 1

        def __init__(self):
            pass

        async def create_user(self, name: str, email: str, hashed_password: str):
            # Simulate duplicate‑key error based on normalized email
            for doc in self._data.values():
                if doc["email_normalized"] == email.strip().lower():
                    # Raise the same exception type the real repo would raise
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError("duplicate key error")
            user_id = str(self._id_counter)
            self._id_counter += 1
            doc = {
                "_id": user_id,
                "name": name,
                "email": email,
                "email_normalized": email.strip().lower(),
                "hashed_password": hashed_password,
            }
            self._data[user_id] = doc
            return doc

        async def find_by_email(self, email: str):
            normalized = email.strip().lower()
            for doc in self._data.values():
                if doc["email_normalized"] == normalized:
                    return doc
            return None

        async def get_by_id(self, user_id: str):
            return self._data.get(user_id)

    # Patch the class used throughout the codebase
    monkeypatch.setattr("app.repositories.user.UserRepository", FakeRepository)
    monkeypatch.setattr("app.services.auth.UserRepository", FakeRepository)
    monkeypatch.setattr("app.core.dependencies.UserRepository", FakeRepository)
     # Recreate the module‑level AuthService instance so it uses the patched repo
    import importlib
    import app.api.routes.auth as auth_routes
    importlib.reload(auth_routes)
    auth_routes.auth_service = auth_routes.AuthService()
    yield

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def register_user(client: TestClient, name: str, email: str, password: str):
    return client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )

def login_user(client: TestClient, email: str, password: str):
    return client.post(
        "/auth/login", json={"email": email, "password": password}
    )

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_successful_registration(client: TestClient):
    resp = register_user(client, "Alice", "alice@example.com", "secret123")
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]  # id is returned
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    # The password hash must not be exposed
    assert "hashed_password" not in data

def test_duplicate_email_registration(client: TestClient):
    # First registration succeeds
    resp1 = register_user(client, "Bob", "bob@example.com", "pwd123")
    assert resp1.status_code == 201
    # Second registration with same email (different case) should fail
    resp2 = register_user(client, "Bobby", "BOB@EXAMPLE.COM", "pwd456")
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "Email already registered"

def test_email_normalization_on_registration(client: TestClient):
    resp = register_user(client, "Carol", "CaRol@Example.COM", "pass123")
    assert resp.status_code == 201
    data = resp.json()
    # The stored email is returned as‑is (original case), but the repository
    # normalizes the lookup value, which we verify via a subsequent login.
    login_resp = login_user(client, "carol@example.com", "pass123")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    payload = decode_access_token(token)
    # The ``sub`` claim should contain the user id created above
    assert payload["sub"] == data["id"]

def test_password_is_hashed_and_not_returned(client: TestClient):
    resp = register_user(client, "Dave", "dave@example.com", "mysecret")
    assert resp.status_code == 201
    data = resp.json()
    # The response should never contain the password or its hash
    assert "password" not in data
    assert "hashed_password" not in data
    # Verify that login works – the stored hash is used internally
    login_resp = login_user(client, "dave@example.com", "mysecret")
    assert login_resp.status_code == 200

def test_successful_login(client: TestClient):
    # Register first
    register_user(client, "Eve", "eve@example.com", "evesecret")
    resp = login_user(client, "eve@example.com", "evesecret")
    assert resp.status_code == 200
    json = resp.json()
    assert "access_token" in json
    assert json["token_type"] == "bearer"
    # Validate token payload
    payload = decode_access_token(json["access_token"])
    assert "sub" in payload

def test_login_incorrect_password(client: TestClient):
    register_user(client, "Frank", "frank@example.com", "correctpwd")
    resp = login_user(client, "frank@example.com", "wrongpwd")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"

def test_login_unknown_email(client: TestClient):
    resp = login_user(client, "nonexistent@example.com", "anypwd")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"

def test_me_endpoint_with_valid_token(client: TestClient):
    # Register and obtain a token
    reg = register_user(client, "Grace", "grace@example.com", "gracepwd")
    token = login_user(client, "grace@example.com", "gracepwd").json()["access_token"]
    # Call /auth/me with the token
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "grace@example.com"
    assert data["name"] == "Grace"
    # Ensure no password fields are present
    assert "hashed_password" not in data

def test_me_endpoint_without_token(client: TestClient):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing authentication token"

def test_me_endpoint_with_invalid_token(client: TestClient):
    # Use a syntactically valid but wrong token
    fake_token = "invalid.token.signature"
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert resp.status_code == 401
    # The exact error message comes from the dependency raising JWTError
    assert resp.json()["detail"] == "Invalid or expired token"
