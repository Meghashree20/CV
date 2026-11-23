"""Liveness route. Does not run a model or read image data."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health import build_health_report

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return await build_health_report()
