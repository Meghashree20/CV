
"""API tests for authenticated image management."""

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app.api.routes.images import image_service
from app.core.dependencies import get_current_user


class FakeImageRepository:
    """In-memory image repository for API tests."""

    def __init__(self):
        self.images = []

    async def create_image(
        self, user_id, filename, content_type,
        size_bytes, width, height, uploaded_at
    ):
        document = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "width": width,
            "height": height,
            "uploaded_at": uploaded_at,
        }
        self.images.append(document)
        return document

    async def list_by_user(self, user_id, limit=100):
        return [
            item for item in self.images
            if item["user_id"] == user_id
        ][:limit]

    async def get_by_id(self, image_id, user_id):
        for item in self.images:
            if (
                item["_id"] == image_id
                and item["user_id"] == user_id
            ):
                return item
        return None

    async def delete_by_id(self, image_id, user_id):
        for item in self.images:
            if (
                item["_id"] == image_id
                and item["user_id"] == user_id
            ):
                self.images.remove(item)
                return True
        return False


def make_image_bytes():
    """Create a small valid JPEG image for testing."""

    buffer = BytesIO()
    image = Image.new("RGB", (20, 20), color="white")
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def image_api_setup(client, monkeypatch, tmp_path):
    """Configure fake storage, repository and authentication."""

    repo = FakeImageRepository()

    monkeypatch.setattr(image_service, "repo", repo)
    monkeypatch.setattr(
        image_service.settings,
        "image_storage_path",
        tmp_path,
    )

    current_user = {
        "_id": "image-user-1",
        "name": "Test User",
        "email": "test@example.com",
    }

    previous_overrides = dict(client.app.dependency_overrides)

    client.app.dependency_overrides[get_current_user] = (
        lambda: current_user
    )

    yield repo, current_user, tmp_path

    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(previous_overrides)


def test_upload_image(client, image_api_setup):
    repo, current_user, storage_dir = image_api_setup

    response = client.post(
        "/images/upload",
        files={
            "file": (
                "face.jpg",
                make_image_bytes(),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["content_type"] == "image/jpeg"
    assert data["width"] == 20
    assert data["height"] == 20
    assert data["size_bytes"] > 0
    assert "filename" not in data
    assert "file_path" not in data

    assert len(repo.images) == 1
    assert repo.images[0]["user_id"] == current_user["_id"]

    stored_file = storage_dir / repo.images[0]["filename"]
    assert stored_file.is_file()


def test_list_only_own_images(client, image_api_setup):
    repo, current_user, _ = image_api_setup

    now = datetime.now(timezone.utc)

    repo.images.extend([
        {
            "_id": "own-image",
            "user_id": current_user["_id"],
            "filename": "own.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 100,
            "width": 20,
            "height": 20,
            "uploaded_at": now,
        },
        {
            "_id": "other-image",
            "user_id": "another-user",
            "filename": "other.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 100,
            "width": 20,
            "height": 20,
            "uploaded_at": now,
        },
    ])

    response = client.get("/images")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == "own-image"


def test_get_own_image(client, image_api_setup):
    repo, current_user, storage_dir = image_api_setup

    image_bytes = make_image_bytes()
    filename = "test-image.jpg"
    (storage_dir / filename).write_bytes(image_bytes)

    repo.images.append({
        "_id": "own-image",
        "user_id": current_user["_id"],
        "filename": filename,
        "content_type": "image/jpeg",
        "size_bytes": len(image_bytes),
        "width": 20,
        "height": 20,
        "uploaded_at": datetime.now(timezone.utc),
    })

    response = client.get("/images/own-image")

    assert response.status_code == 200
    assert response.content == image_bytes
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_cannot_get_another_users_image(client, image_api_setup):
    repo, _, storage_dir = image_api_setup

    filename = "other-user.jpg"
    (storage_dir / filename).write_bytes(make_image_bytes())

    repo.images.append({
        "_id": "other-image",
        "user_id": "another-user",
        "filename": filename,
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "width": 20,
        "height": 20,
        "uploaded_at": datetime.now(timezone.utc),
    })

    response = client.get("/images/other-image")

    assert response.status_code == 404


def test_delete_own_image(client, image_api_setup):
    repo, current_user, storage_dir = image_api_setup

    filename = "delete-me.jpg"
    file_path = storage_dir / filename
    file_path.write_bytes(make_image_bytes())

    repo.images.append({
        "_id": "delete-image",
        "user_id": current_user["_id"],
        "filename": filename,
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "width": 20,
        "height": 20,
        "uploaded_at": datetime.now(timezone.utc),
    })

    response = client.delete("/images/delete-image")

    assert response.status_code == 204
    assert not file_path.exists()
    assert len(repo.images) == 0


def test_cannot_delete_another_users_image(client, image_api_setup):
    repo, _, storage_dir = image_api_setup

    filename = "protected.jpg"
    file_path = storage_dir / filename
    file_path.write_bytes(make_image_bytes())

    repo.images.append({
        "_id": "protected-image",
        "user_id": "another-user",
        "filename": filename,
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "width": 20,
        "height": 20,
        "uploaded_at": datetime.now(timezone.utc),
    })

    response = client.delete("/images/protected-image")

    assert response.status_code == 404
    assert file_path.exists()
    assert len(repo.images) == 1


def test_missing_authentication_returns_401(
    client, image_api_setup
):
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get("/images")

    assert response.status_code == 401


def test_missing_physical_file_returns_404(
    client, image_api_setup
):
    repo, current_user, _ = image_api_setup

    repo.images.append({
        "_id": "missing-file",
        "user_id": current_user["_id"],
        "filename": "does-not-exist.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "width": 20,
        "height": 20,
        "uploaded_at": datetime.now(timezone.utc),
    })

    response = client.get("/images/missing-file")

    assert response.status_code == 404
