"""Preprocess stored images without modifying the original files."""

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.services.image import ImageService


class ImagePreprocessingService:
    """Normalize an uploaded image and return preprocessing metadata."""

    def __init__(self) -> None:
        self.image_service = ImageService()
        self.settings = get_settings()

    async def preprocess(self, image_id: str, user_id: str) -> dict:
        """Preprocess an image after checking ownership and existence."""
        result = await self.image_service.get_image(image_id, user_id)
        file_path: Path = result["file_path"]

        processed = None
        intermediate = None
        intermediate_is_original = False
        try:
            with Image.open(file_path) as original:
                original_width, original_height = original.size
                original_format = original.format

                # Apply EXIF orientation – may return a new image object
                intermediate = ImageOps.exif_transpose(original)
                intermediate_is_original = intermediate is original
                # Convert to RGB for consistent processing
                processed = intermediate.convert("RGB")

                max_dim = self.settings.max_image_dimension_px
                if max_dim is not None and max(processed.size) > max_dim:
                    processed.thumbnail(
                        (max_dim, max_dim),
                        Image.Resampling.LANCZOS,
                    )

                processed_width, processed_height = processed.size
                color_mode = processed.mode
        except (UnidentifiedImageError, OSError) as exc:
            raise AppError(
                message="Image file is corrupted or unsupported",
                status_code=400,
                code="invalid_image_file",
            ) from exc
        finally:
            # Close the processed image if it was created
            if processed is not None:
                try:
                    processed.close()
                except Exception:
                    pass
            # Close the intermediate image only if it is a distinct object
            if intermediate is not None and not intermediate_is_original:
                try:
                    intermediate.close()
                except Exception:
                    pass

        return {
            "image_id": str(image_id),
            "original_width": original_width,
            "original_height": original_height,
            "processed_width": processed_width,
            "processed_height": processed_height,
            "color_mode": color_mode,
            "format": original_format,
            "preprocessing_status": "success",
        }
