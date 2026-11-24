"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.api.routes.users import router as users_router
from app.core.middleware import RequestLoggingMiddleware
from app.db.mongo import mongo

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Starting %s %s (environment=%s)",
            settings.app_name,
            __version__,
            settings.environment,
        )
        logger.info("CORS origins: %s", ", ".join(settings.cors_origin_list))

        connected = await mongo.connect()

        if connected:
            try:
                await mongo.ensure_indexes()
            except Exception:
                logger.exception("Failed to initialize MongoDB indexes")

        try:
            yield
        finally:
            await mongo.disconnect()
            logger.info("Stopped %s", settings.app_name)


    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="Backend foundation for personalized skin analysis.",
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    register_exception_handlers(app)
    # Include routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    return app


app = create_app()
