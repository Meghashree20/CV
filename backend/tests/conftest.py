"""Test environment is set before the application is imported."""

import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["APP_NAME"] = "Skin Analysis API"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017"
os.environ["MONGODB_DB_NAME"] = "skin_analysis_test"
os.environ["MONGODB_SERVER_SELECTION_TIMEOUT_MS"] = "500"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRATION_SECONDS"] = "3600"


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
