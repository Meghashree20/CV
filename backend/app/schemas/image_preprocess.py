'''Pydantic schema for image preprocessing response.'''

from pydantic import BaseModel, ConfigDict, Field


class ImagePreprocessResponse(BaseModel):
    """Metadata returned after preprocessing an uploaded image.
    No file data is sent, only details about the transformation.
    """

    image_id: str = Field(description="Identifier of the processed image")
    original_width: int = Field(gt=0, description="Original image width in pixels")
    original_height: int = Field(gt=0, description="Original image height in pixels")
    processed_width: int = Field(gt=0, description="Width after resizing (may equal original)")
    processed_height: int = Field(gt=0, description="Height after resizing (may equal original)")
    color_mode: str = Field(description="Pillow color mode after conversion, e.g., 'RGB'")
    format: str | None = Field(description="Original uploaded image format, e.g., 'JPEG' or 'PNG'")
    preprocessing_status: str = Field(default="success", description="Result status")

    model_config = ConfigDict(extra="forbid")

