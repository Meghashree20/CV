"""Environment-backed settings. Secrets stay in the environment, not in code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and an optional .env file.
    Includes JWT configuration for authentication.
    """

    # ----- core application settings -----
    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Skin Analysis API"
    environment: str = "development"
    log_level: str = "INFO"
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string. Override in the environment.",
    )
    mongodb_db_name: str = "skin_analysis"
    mongodb_server_selection_timeout_ms: int = Field(default=2000, ge=100, le=30000)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ----- JWT settings -----
    jwt_secret_key: str = Field(..., description="Secret key for signing JWTs")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiration_seconds: int = Field(default=3600, ge=60, description="JWT TTL in seconds")

    # ---------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------
    @field_validator("environment")
    @classmethod
    def environment_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("ENVIRONMENT must not be blank")
        return cleaned

    @field_validator("log_level")
    @classmethod
    def log_level_known(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        cleaned = value.strip().upper()
        if cleaned not in allowed:
            raise ValueError(
                f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}"
            )
        return cleaned

    @field_validator("mongodb_uri")
    @classmethod
    def mongodb_uri_scheme(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError(
                "MONGODB_URI must start with mongodb:// or mongodb+srv://"
            )
        return cleaned

    @field_validator("mongodb_db_name")
    @classmethod
    def database_name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("MONGODB_DB_NAME must not be blank")
        return cleaned

    @field_validator("cors_origins")
    @classmethod
    def cors_origins_not_empty(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one origin")
        return ",".join(origins)

    @field_validator("jwt_secret_key")
    @classmethod
    def jwt_secret_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("JWT_SECRET_KEY must be provided and not blank")
        return cleaned

    # ---------------------------------------------------------------------
    # Helper properties
    # ---------------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
