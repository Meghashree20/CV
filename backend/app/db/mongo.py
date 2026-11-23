"""Async MongoDB client. A failed ping does not stop the API process."""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MongoManager:
    """Owns the Motor client for the process lifetime."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None

    async def connect(self) -> bool:
        settings = get_settings()
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            )
        except Exception:
            self.client = None
            self.database = None
            logger.warning("MongoDB client could not be created", exc_info=True)
            return False

        if not await self.ping():
            self.database = None
            logger.warning(
                "MongoDB is unavailable. The API will stay up and /health will report degraded."
            )
            return False

        self.database = self.client[settings.mongodb_db_name]
        logger.info("MongoDB ping succeeded for database %s", settings.mongodb_db_name)
        return True

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
        except Exception:
            logger.warning("MongoDB ping failed", exc_info=True)
            return False
        return True

    async def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()
        self.client = None
        self.database = None
        logger.info("MongoDB client closed")


mongo = MongoManager()
