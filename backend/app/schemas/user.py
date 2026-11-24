


"""Pydantic schemas for user profile management."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRead(BaseModel):
    """Public user profile; never includes password credentials."""

    id: str
    name: str
    email: str
    age: int | None = None
    gender: str | None = None
    skin_type: str | None = None
    skin_concerns: list[str] | None = None
    skincare_goals: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Fields that an authenticated user may partially update."""

    name: str | None = Field(default=None, min_length=1)
    age: int | None = Field(default=None, ge=0, le=130)
    gender: Literal["male", "female", "other"] | None = None
    skin_type: Literal[
        "oily", "dry", "combination", "normal", "sensitive"
    ] | None = None
    skin_concerns: list[str] | None = None
    skincare_goals: list[str] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            raise ValueError("name cannot be null")
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("name cannot be empty")
        return value

    @field_validator("skin_concerns", "skincare_goals")
    @classmethod
    def validate_string_lists(cls, values):
        if values is None:
            return None

        cleaned = []
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("List items must be non-empty strings")
            cleaned.append(value.strip())
        return cleaned
