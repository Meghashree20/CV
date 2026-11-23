"""Build the live health report from configuration and a MongoDB ping."""

from app.core.config import get_settings
from app.db.mongo import mongo
from app.schemas.health import HealthResponse


async def build_health_report() -> HealthResponse:
    settings = get_settings()
    mongodb_ok = await mongo.ping()
    return HealthResponse(
        status="ok" if mongodb_ok else "degraded",
        api="ok",
        mongodb="connected" if mongodb_ok else "unavailable",
        environment=settings.environment,
        service=settings.app_name,
    )
