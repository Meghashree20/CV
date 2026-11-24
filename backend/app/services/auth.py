"""Authentication service layer.
Handles registration, login and user lookup.
"""

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password, create_access_token
from app.repositories.user import UserRepository
from app.schemas.auth import UserCreate, UserRead


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(self, payload: UserCreate) -> UserRead:
        # Normalize email
        email_norm = payload.email.strip().lower()
        existing = await self.repo.find_by_email(email_norm)
        if existing:
            raise AppError(message="Email already registered", status_code=409, code="duplicate_email")
        hashed = hash_password(payload.password)
        user_doc = await self.repo.create_user(name=payload.name, email=payload.email.strip(), hashed_password=hashed)
        return UserRead(id=str(user_doc["_id"]), name=user_doc["name"], email=user_doc["email"])

    async def login(self, email: str, password: str) -> str:
        # Normalize email for lookup
        email_norm = email.strip().lower()
        user = await self.repo.find_by_email(email_norm)
        if not user:
            raise AppError(message="Invalid credentials", status_code=401, code="invalid_credentials")
        if not verify_password(password, user["hashed_password"]):
            raise AppError(message="Invalid credentials", status_code=401, code="invalid_credentials")
        token = create_access_token(subject=str(user["_id"]))
        return token

    async def get_user_profile(self, user_id: str) -> UserRead:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppError(message="User not found", status_code=404, code="user_not_found")
        return UserRead(id=str(user["_id"]), name=user["name"], email=user["email"]) 

