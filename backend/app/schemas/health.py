"""Health check response."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = Field(
        description="ok when MongoDB answered a ping; degraded when it did not."
    )
    api: Literal["ok"]
    mongodb: Literal["connected", "unavailable"]
    environment: str
    service: str
