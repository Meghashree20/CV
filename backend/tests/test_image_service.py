
"""Tests for image upload validation and private storage."""

import asyncio
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers
from PIL import Image

from app.core.exceptions import AppError
from app.services.image import ImageService


USER_ID = "507f1f77bcf86cd799439011"


class FakeImageRepository:
    """Fake repository that avoids connecting to MongoDB."""

    def __init__(self):
        self.created_images = []
        self.should_fail = False

    async def create_image(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("Simulated database failure")

        document = {
            "_id": "image-test-123",
            **kwargs,
        }
        self.created_images.append(document)
        return document


def create_image_bytes(image_format):
    """Create a small valid image in memory."""

    buffer = BytesIO()

    Image.new("RGB", (16, 16), color=(100, 150, 200)).save(
        buffer,
        format=image_format,
    )

    return buffer.getvalue()


def create_upload(data, content_type, filename="test-image"):
    """Create a FastAPI UploadFile for testing."""

    return UploadFile(
        file=BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def image_service(tmp_path):
    """Create an image service using isolated temporary storage."""

    service = ImageService()

    service.settings = SimpleNamespace(
        image_storage_path=tmp_path,
        max_image_upload_size_mb=5,
    )

    service.repo = FakeImageRepository()

    return service


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [
        ("JPEG", "image/jpeg"),
        ("PNG", "image/png"),
        ("WEBP", "image/webp"),
    ],
)
def test_valid_image_upload(
    image_service,
    tmp_path,
    image_format,
    content_type,
):
    data = create_image_bytes(image_format)
    upload = create_upload(data, content_type)

    result = asyncio.run(
        image_service.upload_image(USER_ID, upload)
    )

    assert result.id == "image-test-123"
    assert result.content_type == content_type
    assert result.size_bytes == len(data)
    assert result.width == 16
    assert result.height == 16

    stored_files = list(tmp_path.iterdir())

    assert len(stored_files) == 1
    assert stored_files[0].suffix in {".jpg", ".png", ".webp"}
    assert stored_files[0].read_bytes() == data

    assert len(image_service.repo.created_images) == 1

    metadata = image_service.repo.created_images[0]

    assert metadata["filename"] == stored_files[0].name
    assert metadata["user_id"] == USER_ID
    assert "image_data" not in metadata
    assert "storage_path" not in metadata


def test_empty_upload_is_rejected(image_service, tmp_path):
    upload = create_upload(b"", "image/jpeg")

    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "empty_image"
    assert list(tmp_path.iterdir()) == []


def test_corrupted_image_is_rejected(image_service, tmp_path):
    upload = create_upload(b"not-a-real-image", "image/jpeg")

    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert exc_info.value.code == "invalid_image"
    assert list(tmp_path.iterdir()) == []


def test_unsupported_image_format_is_rejected(
    image_service,
    tmp_path,
):
    data = create_image_bytes("GIF")
    upload = create_upload(data, "image/gif")

    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert exc_info.value.status_code == 415
    assert exc_info.value.code == "unsupported_image_format"
    assert list(tmp_path.iterdir()) == []


def test_content_type_mismatch_is_rejected(
    image_service,
    tmp_path,
):
    data = create_image_bytes("JPEG")
    upload = create_upload(data, "image/png")

    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert exc_info.value.code == "image_content_type_mismatch"
    assert list(tmp_path.iterdir()) == []


def test_oversized_upload_is_rejected(image_service, tmp_path):
    max_bytes = 5 * 1024 * 1024
    data = b"x" * (max_bytes + 1)

    upload = create_upload(data, "image/jpeg")

    with pytest.raises(AppError) as exc_info:
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert exc_info.value.status_code == 413
    assert exc_info.value.code == "image_too_large"
    assert list(tmp_path.iterdir()) == []


def test_stored_file_is_removed_when_repository_fails(
    image_service,
    tmp_path,
):
    image_service.repo.should_fail = True

    data = create_image_bytes("JPEG")
    upload = create_upload(data, "image/jpeg")

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        asyncio.run(
            image_service.upload_image(USER_ID, upload)
        )

    assert list(tmp_path.iterdir()) == []
