
"""User profile routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.core.exceptions import AppError
from app.schemas.user import UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])

user_service = UserService()


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: dict = Depends(get_current_user),
):
    try:
        return await user_service.get_profile(
            str(current_user["_id"])
        )
    except AppError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )


@router.put("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await user_service.update_profile(
            str(current_user["_id"]),
            payload,
        )
    except AppError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )
