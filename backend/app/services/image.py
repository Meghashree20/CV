
"""Image upload service with validation and private local storage."""

import os
import tempfile
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.repositories.image import ImageRepository
from app.schemas.image import ImageRead


class ImageService:
    """Validates, stores and manages users' uploaded images."""

    ALLOWED_FORMATS = {
        "JPEG": ("image/jpeg", ".jpg"),
        "PNG": ("image/png", ".png"),
        "WEBP": ("image/webp", ".webp"),
    }

    CHUNK_SIZE = 64 * 1024

    def __init__(self) -> None:
        self.repo = ImageRepository()
        self.settings = get_settings()

    async def upload_image(
        self,
        user_id: str,
        upload_file: UploadFile,
    ) -> ImageRead:
        """Validate and store an image, then save its metadata."""

        storage_dir = Path(self.settings.image_storage_path)
        max_bytes = self.settings.max_image_upload_size_mb * 1024 * 1024

        temp_path: Path | None = None
        final_path: Path | None = None

        try:
            storage_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".upload",
                dir=storage_dir,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                total_bytes = 0

                while True:
                    chunk = await upload_file.read(self.CHUNK_SIZE)

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > max_bytes:
                        raise AppError(
                            message="Image exceeds the maximum upload size",
                            status_code=413,
                            code="image_too_large",
                        )

                    temp_file.write(chunk)

            if total_bytes == 0:
                raise AppError(
                    message="Uploaded image is empty",
                    status_code=400,
                    code="empty_image",
                )

            try:
                with warnings.catch_warnings():
                    warnings.simplefilter(
                        "error",
                        Image.DecompressionBombWarning,
                    )

                    with Image.open(temp_path) as image:
                        image.verify()

                    with Image.open(temp_path) as image:
                        image.load()
                        image_format = image.format
                        width, height = image.size

            except (
                UnidentifiedImageError,
                OSError,
                Image.DecompressionBombError,
                Image.DecompressionBombWarning,
            ) as exc:
                raise AppError(
                    message="Uploaded file is not a valid supported image",
                    status_code=400,
                    code="invalid_image",
                ) from exc

            if image_format not in self.ALLOWED_FORMATS:
                raise AppError(
                    message="Only JPEG, PNG and WebP images are supported",
                    status_code=415,
                    code="unsupported_image_format",
                )

            expected_type, extension = self.ALLOWED_FORMATS[image_format]

            if upload_file.content_type != expected_type:
                raise AppError(
                    message="Image content type does not match its actual format",
                    status_code=400,
                    code="image_content_type_mismatch",
                )

            filename = f"{uuid.uuid4().hex}{extension}"
            final_path = storage_dir / filename

            os.replace(temp_path, final_path)
            temp_path = None

            uploaded_at = datetime.now(timezone.utc)

            try:
                document = await self.repo.create_image(
                    user_id=user_id,
                    filename=filename,
                    content_type=expected_type,
                    size_bytes=total_bytes,
                    width=width,
                    height=height,
                    uploaded_at=uploaded_at,
                )
            except Exception:
                final_path.unlink(missing_ok=True)
                final_path = None
                raise

            return self._to_image_read(document)

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    async def list_images(self, user_id: str) -> list[ImageRead]:
        """Return metadata for images belonging to the user."""

        documents = await self.repo.list_by_user(user_id)

        return [
            self._to_image_read(document)
            for document in documents
        ]

    async def get_image(self, image_id: str, user_id: str) -> dict:
        """Find an image belonging to the user and verify its file exists."""

        document = await self.repo.get_by_id(image_id, user_id)

        if not document:
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

        filename = document["filename"]

        if Path(filename).name != filename:
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

        file_path = Path(self.settings.image_storage_path) / filename

        if not file_path.is_file():
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

        return {
            "document": self._to_image_read(document),
            "file_path": file_path,
            "content_type": document["content_type"],
        }

    async def delete_image(self, image_id: str, user_id: str) -> None:
        """Delete an image only when it belongs to the user."""

        document = await self.repo.get_by_id(image_id, user_id)

        if not document:
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

        filename = document["filename"]

        if Path(filename).name != filename:
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

        file_path = Path(self.settings.image_storage_path) / filename

        # Remove the private file before deleting its metadata.
        if file_path.exists():
            file_path.unlink()

        deleted = await self.repo.delete_by_id(image_id, user_id)

        if not deleted:
            raise AppError(
                message="Image not found",
                status_code=404,
                code="image_not_found",
            )

    @staticmethod
    def _to_image_read(document: dict) -> ImageRead:
        """Convert a MongoDB document into safe public metadata."""

        return ImageRead(
            id=str(document["_id"]),
            content_type=document["content_type"],
            size_bytes=document["size_bytes"],
            width=document["width"],
            height=document["height"],
            uploaded_at=document["uploaded_at"],
        )
