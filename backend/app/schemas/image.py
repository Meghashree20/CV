"""Pydantic schemas for image upload and metadata responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageRead(BaseModel):
    """Public image metadata; never exposes the physical storage path."""

    id: str
    content_type: Literal[
        "image/jpeg",
        "image/png",
        "image/webp",
    ]
    size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    uploaded_at: datetime

    model_config = ConfigDict(extra="forbid")