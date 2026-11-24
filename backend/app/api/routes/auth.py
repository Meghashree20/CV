"""Authentication API routes.
Provides registration, login and profile endpoints under /auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.exceptions import AppError
from app.core.dependencies import get_current_user
from app.schemas.auth import UserCreate, UserRead, UserLogin, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

auth_service = AuthService()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    try:
        return await auth_service.register(payload)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    try:
        token = await auth_service.login(email=payload.email, password=payload.password)
        return TokenResponse(access_token=token)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/me", response_model=UserRead)
async def me(current_user: dict = Depends(get_current_user)):
    # current_user is the raw document from Mongo
    return UserRead(id=str(current_user["_id"]), name=current_user["name"], email=current_user["email"]) 

