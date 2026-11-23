"""Test environment is set before the application is imported."""

import os

os.environ["APP_NAME"] = "Skin Analysis API"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB_NAME"] = "skin_analysis_test"
os.environ["MONGODB_SERVER_SELECTION_TIMEOUT_MS"] = "500"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def client():
    from app.main import create_app

    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
