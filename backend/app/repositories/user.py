
"""User repository for MongoDB."""

from typing import Optional

from app.db.mongo import mongo


class UserRepository:
    """Provides asynchronous access to the users collection."""

    @property
    def collection(self):
        if mongo.database is None:
            raise RuntimeError("MongoDB is not connected")

        return mongo.database["users"]

    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
    ) -> dict:
        doc = {
            "name": name,
            "email": email.strip(),
            "email_normalized": email.strip().lower(),
            "hashed_password": hashed_password,
        }

        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def find_by_email(self, email: str) -> Optional[dict]:
        normalized = email.strip().lower()

        return await self.collection.find_one(
            {"email_normalized": normalized}
        )

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        from bson import ObjectId

        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None

        return await self.collection.find_one({"_id": object_id})

    async def update_profile(
        self, user_id: str, update_data: dict
    ) -> Optional[dict]:
        from bson import ObjectId
        from pymongo import ReturnDocument

        allowed_fields = {
            "name",
            "age",
            "gender",
            "skin_type",
            "skin_concerns",
            "skincare_goals",
        }

        if not update_data or not set(update_data).issubset(allowed_fields):
            raise ValueError("Invalid profile update fields")

        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None

        return await self.collection.find_one_and_update(
            {"_id": object_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )
