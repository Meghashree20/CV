"""MongoDB repository for uploaded image metadata."""

from datetime import datetime

from bson import ObjectId

from app.db.mongo import mongo


class ImageRepository:
    """Handles image metadata stored in MongoDB."""

    @property
    def collection(self):
        if mongo.database is None:
            raise RuntimeError("MongoDB is not connected")
        return mongo.database["images"]

    async def create_image(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        width: int,
        height: int,
        uploaded_at: datetime,
    ) -> dict:
        """Save metadata for an uploaded image."""

        try:
            owner_id = ObjectId(user_id)
        except Exception as exc:
            raise ValueError("Invalid user ID") from exc

        document = {
            "user_id": owner_id,
            "filename": filename,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "width": width,
            "height": height,
            "uploaded_at": uploaded_at,
        }

        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return document

    async def get_by_id(
        self,
        image_id: str,
        user_id: str,
    ) -> dict | None:
        """Find an image only if it belongs to the specified user."""

        try:
            image_object_id = ObjectId(image_id)
            owner_id = ObjectId(user_id)
        except Exception:
            return None

        return await self.collection.find_one(
            {
                "_id": image_object_id,
                "user_id": owner_id,
            }
        )

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """Return the specified user's images, newest first."""

        try:
            owner_id = ObjectId(user_id)
        except Exception:
            return []

        cursor = (
            self.collection
            .find({"user_id": owner_id})
            .sort("uploaded_at", -1)
            .limit(limit)
        )

        return await cursor.to_list(length=limit)

    async def delete_by_id(
        self,
        image_id: str,
        user_id: str,
    ) -> bool:
        """Delete metadata only when the image belongs to the user."""

        try:
            image_object_id = ObjectId(image_id)
            owner_id = ObjectId(user_id)
        except Exception:
            return False

        result = await self.collection.delete_one(
            {
                "_id": image_object_id,
                "user_id": owner_id,
            }
        )

        return result.deleted_count == 1
