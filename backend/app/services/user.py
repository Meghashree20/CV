
"""User profile service layer."""

from app.core.exceptions import AppError
from app.repositories.user import UserRepository
from app.schemas.user import UserRead, UserUpdate


class UserService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def get_profile(self, user_id: str) -> UserRead:
        user = await self.repo.get_by_id(user_id)

        if not user:
            raise AppError(
                message="User not found",
                status_code=404,
                code="user_not_found",
            )

        return self._to_user_read(user)

    async def update_profile(
        self, user_id: str, payload: UserUpdate
    ) -> UserRead:
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            raise AppError(
                message="No fields to update",
                status_code=400,
                code="empty_update",
            )

        updated = await self.repo.update_profile(user_id, update_data)

        if not updated:
            raise AppError(
                message="User not found",
                status_code=404,
                code="user_not_found",
            )

        return self._to_user_read(updated)

    @staticmethod
    def _to_user_read(user: dict) -> UserRead:
        return UserRead(
            id=str(user["_id"]),
            name=user["name"],
            email=user["email"],
            age=user.get("age"),
            gender=user.get("gender"),
            skin_type=user.get("skin_type"),
            skin_concerns=user.get("skin_concerns"),
            skincare_goals=user.get("skincare_goals"),
        )
