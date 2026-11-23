"""Settings load from the environment and reject unsafe values."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_settings_follow_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Config Test API")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://db.example")
    monkeypatch.setenv("MONGODB_DB_NAME", "skin_staging")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example, http://localhost:3000")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "Config Test API"
    assert settings.environment == "staging"
    assert settings.mongodb_uri == "mongodb+srv://db.example"
    assert settings.mongodb_db_name == "skin_staging"
    assert settings.cors_origin_list == ["https://app.example", "http://localhost:3000"]
    assert settings.log_level == "DEBUG"


def test_settings_read_env_file(monkeypatch):
    env_file = Path(__file__).parent / "_sample.env"
    env_file.write_text(
        "\n".join(
            [
                "APP_NAME=From File",
                "ENVIRONMENT=development",
                "LOG_LEVEL=INFO",
                "MONGODB_URI=mongodb://mongo.internal:27017",
                "MONGODB_DB_NAME=from_file",
                "CORS_ORIGINS=http://localhost:3000",
            ]
        ),
        encoding="utf-8",
    )
    for name in (
        "APP_NAME",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "MONGODB_URI",
        "MONGODB_DB_NAME",
        "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)

    try:
        settings = Settings(_env_file=env_file)
    finally:
        env_file.unlink(missing_ok=True)

    assert settings.app_name == "From File"
    assert settings.mongodb_uri == "mongodb://mongo.internal:27017"
    assert settings.mongodb_db_name == "from_file"
    assert settings.cors_origin_list == ["http://localhost:3000"]


def test_mongodb_uri_must_use_mongodb_scheme(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "http://localhost:27017")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_origins_cannot_be_blank(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " , ")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_log_level_must_be_known(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "verbose")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
