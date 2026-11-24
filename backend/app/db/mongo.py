
"""Async MongoDB client. A failed connection does not stop the API process."""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

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

            if not await self.ping():
                self.database = None
                logger.warning("MongoDB is unavailable.")
                return False

            self.database = self.client[settings.mongodb_db_name]

            logger.info(
                "MongoDB connected to database %s",
                settings.mongodb_db_name,
            )
            return True

        except Exception:
            logger.exception("MongoDB connection failed")
            self.database = None
            return False

    
    async def ensure_indexes(self) -> None:
        """Create required MongoDB indexes after a successful connection."""

        if self.database is None:
            return

        await self.database["users"].create_index(
            [("email_normalized", ASCENDING)],
            unique=True,
            name="uq_users_email_normalized",
        )

        await self.database["images"].create_index(
            [("filename", ASCENDING)],
            unique=True,
            name="uq_images_filename",
        )

        await self.database["images"].create_index(
            [
                ("user_id", ASCENDING),
                ("uploaded_at", DESCENDING),
            ],
            name="idx_images_user_uploaded_at",
        )

        logger.info("MongoDB indexes ensured")
 

    async def ping(self) -> bool:
        if self.client is None:
            return False

        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            logger.warning("MongoDB ping failed", exc_info=True)
            return False

    async def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()

        self.client = None
        self.database = None
        logger.info("MongoDB client closed")


mongo = MongoManager()
